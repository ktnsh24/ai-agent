"""Conversation persistence — stores chat history in SQLite."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import Settings
from src.models import ChatMessage, ConversationDetail, ConversationSummary, MessageRole

logger = logging.getLogger(__name__)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class ConversationRow(Base):
    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True)
    title = Column(String(200), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageRow(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(32), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_name = Column(String(100), nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ── Abstract Interface ────────────────────────────────────────────────────


class BaseConversationStore(ABC):
    """Abstract interface for conversation persistence."""

    @abstractmethod
    async def create_conversation(self, title: str = "New Conversation") -> str:
        """Create a new conversation. Returns conversation ID."""
        ...

    @abstractmethod
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Add a message to a conversation."""
        ...

    @abstractmethod
    async def get_messages(self, conversation_id: str) -> list[BaseMessage]:
        """Get all messages for a conversation as LangChain messages."""
        ...

    @abstractmethod
    async def list_conversations(self) -> list[ConversationSummary]:
        """List all conversations."""
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> ConversationDetail | None:
        """Get full conversation details."""
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation. Returns True if deleted."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the store."""
        ...


# ── SQLite Implementation ─────────────────────────────────────────────────


class SQLiteConversationStore(BaseConversationStore):
    """Stores conversations in SQLite using async SQLAlchemy."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Conversation store initialized")

    async def create_conversation(self, title: str = "New Conversation") -> str:
        conversation_id = uuid4().hex[:16]
        async with self.async_session() as session:
            async with session.begin():
                session.add(ConversationRow(id=conversation_id, title=title))
        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        async with self.async_session() as session:
            async with session.begin():
                session.add(
                    MessageRow(
                        conversation_id=conversation_id,
                        role=role,
                        content=content,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                    )
                )
                # Update conversation timestamp
                await session.execute(
                    text("UPDATE conversations SET updated_at = :now WHERE id = :id"),
                    {"now": datetime.utcnow(), "id": conversation_id},
                )

    async def get_messages(self, conversation_id: str) -> list[BaseMessage]:
        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT role, content, tool_name, tool_call_id FROM messages "
                    "WHERE conversation_id = :id ORDER BY timestamp ASC"
                ),
                {"id": conversation_id},
            )
            rows = result.fetchall()

        messages: list[BaseMessage] = []
        for row in rows:
            role, content, tool_name, tool_call_id = row
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "tool":
                messages.append(
                    ToolMessage(content=content, tool_call_id=tool_call_id or "", name=tool_name or "")
                )
        return messages

    async def list_conversations(self) -> list[ConversationSummary]:
        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT c.id, c.title, c.created_at, c.updated_at, "
                    "COUNT(m.id) as message_count "
                    "FROM conversations c LEFT JOIN messages m ON c.id = m.conversation_id "
                    "GROUP BY c.id ORDER BY c.updated_at DESC"
                )
            )
            rows = result.fetchall()

        return [
            ConversationSummary(
                id=row[0],
                title=row[1],
                created_at=row[2],
                updated_at=row[3],
                message_count=row[4],
            )
            for row in rows
        ]

    async def get_conversation(self, conversation_id: str) -> ConversationDetail | None:
        async with self.async_session() as session:
            result = await session.execute(
                text("SELECT id, title, created_at, updated_at FROM conversations WHERE id = :id"),
                {"id": conversation_id},
            )
            row = result.fetchone()
            if not row:
                return None

            msg_result = await session.execute(
                text(
                    "SELECT role, content, tool_name, tool_call_id, timestamp FROM messages "
                    "WHERE conversation_id = :id ORDER BY timestamp ASC"
                ),
                {"id": conversation_id},
            )
            msg_rows = msg_result.fetchall()

        messages = [
            ChatMessage(
                role=MessageRole(msg[0]),
                content=msg[1],
                tool_name=msg[2],
                tool_call_id=msg[3],
                timestamp=msg[4],
            )
            for msg in msg_rows
        ]

        return ConversationDetail(
            id=row[0],
            title=row[1],
            messages=messages,
            created_at=row[2],
            updated_at=row[3],
        )

    async def delete_conversation(self, conversation_id: str) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                await session.execute(
                    text("DELETE FROM messages WHERE conversation_id = :id"),
                    {"id": conversation_id},
                )
                result = await session.execute(
                    text("DELETE FROM conversations WHERE id = :id"),
                    {"id": conversation_id},
                )
                return result.rowcount > 0

    async def close(self) -> None:
        await self.engine.dispose()


# ── In-Memory Implementation ─────────────────────────────────────────────


class InMemoryConversationStore(BaseConversationStore):
    """In-memory conversation store for testing."""

    def __init__(self) -> None:
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}

    async def create_conversation(self, title: str = "New Conversation") -> str:
        conversation_id = uuid4().hex[:16]
        now = datetime.utcnow()
        self._conversations[conversation_id] = {
            "id": conversation_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        self._messages[conversation_id] = []
        return conversation_id

    async def add_message(
        self, conversation_id: str, role: str, content: str,
        tool_name: str | None = None, tool_call_id: str | None = None,
    ) -> None:
        if conversation_id not in self._messages:
            self._messages[conversation_id] = []
        self._messages[conversation_id].append({
            "role": role, "content": content,
            "tool_name": tool_name, "tool_call_id": tool_call_id,
            "timestamp": datetime.utcnow(),
        })
        if conversation_id in self._conversations:
            self._conversations[conversation_id]["updated_at"] = datetime.utcnow()

    async def get_messages(self, conversation_id: str) -> list[BaseMessage]:
        msgs = self._messages.get(conversation_id, [])
        messages: list[BaseMessage] = []
        for m in msgs:
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(AIMessage(content=m["content"]))
            elif m["role"] == "system":
                messages.append(SystemMessage(content=m["content"]))
        return messages

    async def list_conversations(self) -> list[ConversationSummary]:
        return [
            ConversationSummary(
                id=c["id"], title=c["title"],
                message_count=len(self._messages.get(c["id"], [])),
                created_at=c["created_at"], updated_at=c["updated_at"],
            )
            for c in sorted(self._conversations.values(), key=lambda x: x["updated_at"], reverse=True)
        ]

    async def get_conversation(self, conversation_id: str) -> ConversationDetail | None:
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None
        msgs = self._messages.get(conversation_id, [])
        return ConversationDetail(
            id=conv["id"], title=conv["title"],
            messages=[
                ChatMessage(role=MessageRole(m["role"]), content=m["content"],
                            tool_name=m["tool_name"], tool_call_id=m["tool_call_id"],
                            timestamp=m["timestamp"])
                for m in msgs
            ],
            created_at=conv["created_at"], updated_at=conv["updated_at"],
        )

    async def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._messages.pop(conversation_id, None)
            return True
        return False

    async def close(self) -> None:
        pass


# ── Factory ───────────────────────────────────────────────────────────────


def create_conversation_store(settings: Settings) -> BaseConversationStore:
    """Factory: create the appropriate conversation store."""
    if settings.database_url and settings.database_url.startswith("sqlite"):
        return SQLiteConversationStore(settings.database_url)
    return InMemoryConversationStore()
