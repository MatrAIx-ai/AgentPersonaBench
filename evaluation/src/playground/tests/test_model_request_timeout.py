from playground import model_client
from playground.openai_client import OpenAIChatClient


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeCompletion('{"ok": true}')


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    def __init__(self):
        self.chat = _FakeChat()


def test_openai_request_uses_default_timeout():
    fake = _FakeOpenAI()

    client = OpenAIChatClient(client=fake)
    client.complete_json("system", "user")

    assert fake.chat.completions.last_kwargs["timeout"] == 180.0


def test_openai_request_uses_explicit_timeout():
    fake = _FakeOpenAI()

    client = OpenAIChatClient(client=fake, timeout_seconds=45.5)
    client.complete_json("system", "user")

    assert fake.chat.completions.last_kwargs["timeout"] == 45.5


def test_environment_overrides_default_timeout(monkeypatch):
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "75.25")
    fake = _FakeOpenAI()
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: fake)

    client = model_client.build_json_client("openai/gpt-4o-mini")
    client.complete_json("system", "user")

    assert fake.chat.completions.last_kwargs["timeout"] == 75.25


def test_malformed_environment_timeout_uses_default(monkeypatch):
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "not-a-number")
    fake = _FakeOpenAI()
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: fake)

    client = model_client.build_json_client("openai/gpt-4o-mini")
    client.complete_json("system", "user")

    assert fake.chat.completions.last_kwargs["timeout"] == 180.0


def test_build_json_client_propagates_timeout_for_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "92.5")
    fake = _FakeOpenAI()
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: fake)

    client = model_client.build_json_client("openrouter/z-ai/glm-4.7")
    client.complete_json("system", "user")

    assert fake.chat.completions.last_kwargs["timeout"] == 92.5
