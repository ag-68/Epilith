import httpx
import pytest

from llm.base import ChatMessage, LLMRequest
from llm.groq import GroqProvider
from llm.schema import strict_schema
from llm.scripted import ScriptedProvider
from research.models import RedTeamOutput, Thesis


def _walk(node, seen):
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            seen.append(node)
        for value in node.values():
            _walk(value, seen)
    elif isinstance(node, list):
        for item in node:
            _walk(item, seen)


@pytest.mark.parametrize("model", [Thesis, RedTeamOutput])
def test_strict_schema_requires_every_property_everywhere(model):
    schema = strict_schema(model)
    objects: list[dict] = []
    _walk(schema, objects)
    assert objects
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert sorted(obj["required"]) == sorted(obj["properties"].keys())


def _request(model: str) -> LLMRequest:
    return LLMRequest(
        model=model,
        messages=[ChatMessage(role="system", content="s"), ChatMessage(role="user", content="u")],
        json_schema={"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False},
        schema_name="Reply",
        purpose="test",
    )


def test_groq_body_uses_strict_schema_for_supported_models():
    provider = GroqProvider(api_key="k")
    body = provider.build_body(_request("openai/gpt-oss-120b"))
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["messages"][0] == {"role": "system", "content": "s"}


def test_groq_body_falls_back_to_json_object():
    provider = GroqProvider(api_key="k")
    body = provider.build_body(_request("llama-3.3-70b-versatile"))
    assert body["response_format"] == {"type": "json_object"}


def test_groq_requires_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GroqProvider()


def test_groq_parses_reply_and_sends_bearer():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-oss-120b",
                "system_fingerprint": "fp_1",
                "choices": [{"message": {"content": "{\"a\": \"ok\"}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
        )

    provider = GroqProvider(api_key="secret", transport=httpx.MockTransport(handler))
    response = provider.complete(_request("openai/gpt-oss-120b"))
    assert captured["auth"] == "Bearer secret"
    assert captured["url"].endswith("/chat/completions")
    assert response.content == '{"a": "ok"}'
    assert response.model_version == "fp_1"
    assert response.prompt_tokens == 10


def test_scripted_provider_replays_by_purpose():
    provider = ScriptedProvider({"test": {"a": "x"}})
    response = provider.complete(_request("any"))
    assert response.content == '{"a": "x"}'
    with pytest.raises(KeyError):
        provider.complete(_request("any").model_copy(update={"purpose": "other"}))


def test_groq_surfaces_the_providers_own_message_on_refusal():
    # Seen live: a 413 whose body explained a tokens-per-minute limit. The status code alone hid it.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            413,
            json={"error": {"message": "Request too large for model: TPM limit 8000, requested 14925", "code": "rate_limit_exceeded"}},
        )

    provider = GroqProvider(api_key="secret", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match="413.*TPM limit 8000"):
        provider.complete(_request("openai/gpt-oss-120b"))


def test_token_pacer_waits_until_the_minute_window_has_room():
    from llm.groq import TokenPacer

    now = [0.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    pacer = TokenPacer(8000, sleep=sleep, clock=lambda: now[0])
    pacer.wait_for(5000)
    pacer.record(5000)
    pacer.wait_for(2000)  # fits: 7000 <= 8000
    pacer.record(2000)
    pacer.wait_for(3000)  # 10000 > 8000: must wait for the first call to age out
    assert slept and now[0] >= 60
    with pytest.raises(RuntimeError, match="cannot fit"):
        pacer.wait_for(9000)


def test_groq_honours_retry_after_on_429():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(429, headers={"retry-after": "7"}, json={"error": {"message": "slow down"}})
        return httpx.Response(
            200,
            json={"model": "m", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}},
        )

    slept: list[float] = []
    provider = GroqProvider(api_key="secret", transport=httpx.MockTransport(handler), sleep=slept.append)
    provider.complete(_request("openai/gpt-oss-120b"))
    assert slept == [7.0]
