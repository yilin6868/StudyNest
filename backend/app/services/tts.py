"""语音合成服务：edge-tts（微软免费 TTS，中文自然）。

按搭子性别选音色：女生用「晓晓」（温暖），男生用「云希」（阳光）。
失败时抛异常，由 API 层降级为无语音（不打断文字体验）。
"""
import edge_tts

VOICES = {
    "male": "zh-CN-YunxiNeural",
    "female": "zh-CN-XiaoxiaoNeural",
}
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def resolve_voice(gender: str | None) -> str:
    return VOICES.get((gender or "").strip().lower(), DEFAULT_VOICE)


async def synthesize(text: str, gender: str | None = None) -> bytes:
    """文字转语音，返回 MP3 音频字节。"""
    voice = resolve_voice(gender)
    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)
