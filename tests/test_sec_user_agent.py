import pytest

from data.providers.sec_edgar import SecEdgarProvider


def test_accepts_a_real_contact():
    assert SecEdgarProvider(user_agent="Epilith/0.1 (research; someone@example.com)").user_agent


def test_rejects_missing_contact(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(RuntimeError, match="contact email"):
        SecEdgarProvider(user_agent="Epilith/0.1")


@pytest.mark.parametrize(
    "contact",
    ["Epilith ahmet@users.noreply.github.com", "Epilith noreply@example.com", "Epilith No-Reply@Example.com"],
)
def test_rejects_no_reply_addresses(contact: str):
    # SEC answers "Your Request Originates from an Undeclared Automated Tool" to these, on any machine.
    with pytest.raises(RuntimeError, match="no-reply"):
        SecEdgarProvider(user_agent=contact)
