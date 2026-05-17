"""LangGraph agent — the core agent graph with tool-calling loop."""

from __future__ import annotations

import logging
import time
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.config import Settings
from src.llm.provider import BaseLLMProvider
from src.models import AgentResponse, AgentStatus, ToolCall
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools. You can:
1. Search the web for current information
2. Perform mathematical calculations
3. Query a product database with SQL

When answering questions:
- Use tools when you need external information or calculations
- Be concise and accurate
- Cite your sources when using web search
- Show your work when doing calculations
- Format SQL queries clearly

If you don't need a tool, just respond directly."""


# ── Agent State ───────────────────────────────────────────────────────────


class AgentState(TypedDict):
    """State that flows through the agent graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int
    max_iterations: int
    tool_calls_made: list[ToolCall]


# ── Agent Graph Builder ──────────────────────────────────────────────────


class AgentGraph:
    """Builds and manages the LangGraph agent with tool-calling loop."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        settings: Settings,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.settings = settings
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph agent graph."""
        tools = self.tool_registry.get_all_tools()
        llm = self.llm_provider.get_chat_model()

        # Bind tools to the LLM (enables function calling)
        if tools:
            llm_with_tools = llm.bind_tools(tools)
        else:
            llm_with_tools = llm

        # Define the agent node (calls LLM)
        def agent_node(state: AgentState) -> dict:
            """Call the LLM with current messages."""
            messages = state["messages"]
            response = llm_with_tools.invoke(messages)
            print(messages)
            return {
                "messages": [response],
                "iterations": state["iterations"] + 1,
            }

        # Define routing logic
        def should_continue(state: AgentState) -> str:
            """Decide whether to continue to tools or end."""
            messages = state["messages"]
            last_message = messages[-1]

            # Check iteration limit
            if state["iterations"] >= state["max_iterations"]:
                logger.warning("Agent hit max iterations: %d", state["iterations"])
                return "end"

            # Check if LLM wants to use tools
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tools"

            return "end"

        # Build the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        if tools:
            tool_node = ToolNode(tools)
            workflow.add_node("tools", tool_node)

        # Add edges
        workflow.set_entry_point("agent")

        if tools:
            workflow.add_conditional_edges(
                "agent",
                should_continue,
                {"tools": "tools", "end": END},
            )
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)

        return workflow.compile()

    async def run(
        self,
        user_message: str,
        conversation_history: list[BaseMessage] | None = None,
        max_iterations: int | None = None,
    ) -> AgentResponse:
        """Run the agent with a user message.

        Args:
            user_message: The user's input message.
            conversation_history: Optional prior conversation messages.
            max_iterations: Maximum agent loop iterations.

        Returns:
            AgentResponse with the agent's answer and metadata.
        """
        start_time = time.perf_counter()
        max_iter = max_iterations or self.settings.agent_max_iterations

        # Build message list
        messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append(HumanMessage(content=user_message))

        # Initial state
        initial_state: AgentState = {
            "messages": messages,
            "iterations": 0,
            "max_iterations": max_iter,
            "tool_calls_made": [],
        }

        # Run the graph
        try:
            result = await self._graph.ainvoke(initial_state)
        except Exception as e:
            logger.error("Agent execution failed: %s", e)
            return AgentResponse(
                conversation_id=uuid4().hex[:16],
                message=f"I encountered an error: {str(e)}",
                status=AgentStatus.ERROR,
                model=self.llm_provider.get_model_name(),
                provider=self.llm_provider.get_provider_name(),
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Extract response
        result_messages = result["messages"]
        tool_calls_made = self._extract_tool_calls(result_messages)

        # Get the final AI message
        final_message = ""
        for msg in reversed(result_messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_message = msg.content
                break

        latency_ms = (time.perf_counter() - start_time) * 1000
        total_tokens = self._estimate_tokens(result_messages)

        return AgentResponse(
            conversation_id=uuid4().hex[:16],
            message=final_message or "I wasn't able to generate a response.",
            tool_calls=tool_calls_made,
            iterations=result.get("iterations", 0),
            status=AgentStatus.COMPLETE,
            model=self.llm_provider.get_model_name(),
            provider=self.llm_provider.get_provider_name(),
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
        )

    def _extract_tool_calls(self, messages: list[BaseMessage]) -> list[ToolCall]:
        """Extract tool calls and their results from the message history."""
        tool_calls: list[ToolCall] = []
        tool_results: dict[str, str] = {}

        # First pass: collect tool results
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_results[msg.tool_call_id] = msg.content

        # Second pass: collect tool calls and match results
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(
                        ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc["args"],
                            result=tool_results.get(tc["id"]),
                        )
                    )

        return tool_calls

    def _estimate_tokens(self, messages: list[BaseMessage]) -> int:
        """Rough token estimate based on character count."""
        total_chars = sum(len(msg.content) for msg in messages if msg.content)
        return total_chars // 4  # Rough approximation: 1 token ≈ 4 characters


def create_agent_graph(
    llm_provider: BaseLLMProvider,
    tool_registry: ToolRegistry,
    settings: Settings,
) -> AgentGraph:
    """Factory: create the agent graph."""
    return AgentGraph(llm_provider, tool_registry, settings)
