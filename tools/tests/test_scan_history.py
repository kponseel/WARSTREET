"""The history scanner catches real-looking credentials and lets known-safe values pass."""

import pytest

from tools.scan_history import scan_text

# Built at runtime so this file itself never contains a credential-shaped literal.
PASSWORD_URL = (
    "postgresql://postgres.abcd:" + "Rea1Passw0rd" + "@aws-0-eu.pooler.supabase.com:5432/postgres"
)
JWT = "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkw" + "." + "abcdefghijklmnopqrst"
SECRET = "sb_" + "secret_" + "AbCdEf123456789xyz"
EMAIL = "jean.dupont" + "@" + "gmail.com"
PRIVATE_KEY = "-----BEGIN RSA " + "PRIVATE KEY-----"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (f"url = {PASSWORD_URL}", "connection string with password"),
        (f"token {JWT}", "JWT"),
        (f"key {SECRET}", "Supabase secret key"),
        (f"contact {EMAIL}", "email"),
        (PRIVATE_KEY, "private key"),
    ],
)
def test_catches(text: str, kind: str) -> None:
    assert [f.kind for f in scan_text(text, "c", "f")] == [kind]


@pytest.mark.parametrize(
    "text",
    [
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
        "player@example.test and bot@bots.warstreet.invalid",
        "Co-Authored-By: Claude <noreply@anthropic.com>",
        "npx lighthouse@13.5.0",
        "postgresql://[redacted]",
    ],
)
def test_lets_safe_values_pass(text: str) -> None:
    assert scan_text(text, "c", "f") == []
