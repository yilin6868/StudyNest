import pytest

from app.services.chat import chat
from app.services.phrases import PHRASES


@pytest.mark.asyncio
async def test_legacy_chat_entry_is_local_only():
    reply, source = await chat("求鼓励")
    assert source == "local"
    assert reply in PHRASES["encourage"]


@pytest.mark.asyncio
async def test_legacy_chat_entry_never_needs_a_model_key():
    reply, source = await chat("你好")
    assert source == "local"
    assert reply
