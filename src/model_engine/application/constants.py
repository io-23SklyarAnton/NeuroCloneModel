from constants import BASE_PATH

PROMPTS_DIR = BASE_PATH / 'model_engine' / 'infrastructure' / 'llm' / 'prompts'
IMITATION_CONTEXT_TEMPLATE_NAME = 'imitation_context.jinja2'
IMITATION_SYSTEM_PROMPT = (
    "Act as {target_user}. "
    "Continue the chat history organically, "
    "preserving the exact language, typing style, and persona of {target_user}."
)

PERSONA_REPLY_MAX_TOKENS = 256
PERSONA_REPLY_TEMPERATURE = 0.3
PERSONA_REPLY_PRIORITY = 1
PERSONA_REPLY_CONTEXT_WINDOW = 15
