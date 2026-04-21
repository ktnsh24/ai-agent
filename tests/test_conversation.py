"""Tests for conversation persistence."""

import pytest

from src.agent.conversation import InMemoryConversationStore


@pytest.fixture
def store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


class TestInMemoryConversationStore:
    """Test the in-memory conversation store."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, store: InMemoryConversationStore) -> None:
        conv_id = await store.create_conversation("Test Chat")
        assert conv_id is not None
        assert len(conv_id) == 16

    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, store: InMemoryConversationStore) -> None:
        conv_id = await store.create_conversation()
        await store.add_message(conv_id, "user", "Hello!")
        await store.add_message(conv_id, "assistant", "Hi there!")

        messages = await store.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0].content == "Hello!"
        assert messages[1].content == "Hi there!"

    @pytest.mark.asyncio
    async def test_list_conversations(self, store: InMemoryConversationStore) -> None:
        await store.create_conversation("Chat 1")
        await store.create_conversation("Chat 2")
        await store.create_conversation("Chat 3")

        convs = await store.list_conversations()
        assert len(convs) == 3

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, store: InMemoryConversationStore) -> None:
        conv_id = await store.create_conversation("Detailed Chat")
        await store.add_message(conv_id, "user", "What is AI?")
        await store.add_message(conv_id, "assistant", "AI is artificial intelligence.")

        detail = await store.get_conversation(conv_id)
        assert detail is not None
        assert detail.title == "Detailed Chat"
        assert len(detail.messages) == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, store: InMemoryConversationStore) -> None:
        detail = await store.get_conversation("nonexistent")
        assert detail is None

    @pytest.mark.asyncio
    async def test_delete_conversation(self, store: InMemoryConversationStore) -> None:
        conv_id = await store.create_conversation("To Delete")
        await store.add_message(conv_id, "user", "Bye!")

        deleted = await store.delete_conversation(conv_id)
        assert deleted is True

        detail = await store.get_conversation(conv_id)
        assert detail is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, store: InMemoryConversationStore) -> None:
        deleted = await store.delete_conversation("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_conversation_message_count(self, store: InMemoryConversationStore) -> None:
        conv_id = await store.create_conversation()
        for i in range(5):
            await store.add_message(conv_id, "user", f"Message {i}")

        convs = await store.list_conversations()
        assert convs[0].message_count == 5
