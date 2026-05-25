from pathlib import Path

USER_BOT_LIMIT = 5

REPLY_MAX_TOKENS = 256
REPLY_TEMPERATURE = 0.3
REPLY_PRIORITY = 1

PROMPTS_DIR: Path = Path(__file__).resolve().parent.parent / "infrastructure" / "llm" / "prompts"

REPLY_CONTEXT_TEMPLATE_NAME: str = "reply_context.jinja2"

REPLY_SYSTEM_PROMPT: str = (
    "Act as {target_user}. "
    "Continue the chat history organically, "
    "preserving the exact language, typing style, and persona of {target_user}."
)

CONTEXT_WINDOW_MESSAGES: int = 15
