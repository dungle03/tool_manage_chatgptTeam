import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatGPTOAuthSettings:
    enabled: bool
    client_id: str
    auth_url: str
    token_url: str
    redirect_uri: str
    scope: str
    state_ttl_seconds: int


def get_oauth_settings() -> ChatGPTOAuthSettings:
    """Load experimental ChatGPT OAuth settings from environment variables."""
    return ChatGPTOAuthSettings(
        enabled=os.getenv("ENABLE_EXPERIMENTAL_CHATGPT_OAUTH", "false").lower()
        in {"1", "true", "yes", "on"},
        client_id=os.getenv("CHATGPT_OAUTH_CLIENT_ID", "app_EMoamEEZ73f0CkXaXp7hrann"),
        auth_url=os.getenv(
            "CHATGPT_OAUTH_AUTH_URL", "https://auth.openai.com/oauth/authorize"
        ),
        token_url=os.getenv(
            "CHATGPT_OAUTH_TOKEN_URL", "https://auth.openai.com/oauth/token"
        ),
        redirect_uri=os.getenv(
            "CHATGPT_OAUTH_REDIRECT_URI",
            "http://localhost:8000/api/personal-accounts/oauth/callback",
        ),
        scope=os.getenv("CHATGPT_OAUTH_SCOPE", "openid profile email offline_access"),
        state_ttl_seconds=int(os.getenv("CHATGPT_OAUTH_STATE_TTL_SECONDS", "600")),
    )
