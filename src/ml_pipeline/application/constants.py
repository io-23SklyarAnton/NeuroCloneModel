from constants import BASE_PATH

PROMPTS_DIR = BASE_PATH / 'ml_pipeline' / 'infrastructure' / 'llm' / 'prompts'
IMITATION_CONTEXT_TEMPLATE_NAME = 'imitation_context.jinja2'
MAX_CONTEXT_MESSAGES_IMITATION = 15
IMITATION_SYSTEM_PROMPT = "Act as {target_user}. Continue the chat history organically, preserving the exact language, typing style, and persona of {target_user}."

PERSONA_REPLY_MAX_TOKENS = 256
PERSONA_REPLY_TEMPERATURE = 0.3
PERSONA_REPLY_PRIORITY = 1
PERSONA_REPLY_CONTEXT_WINDOW = 15

W_PREV = 60
W_SUB = 10
W_AGG = 10
MAX_WORDS_QUICK_REPLY = 2
MAX_SECONDS_QUICK_REPLY = 60
N_ATTEMPTS = 5

MAX_TOKENS_THREAD_DECISION = 3
TEMP_THREAD_DECISION = 0.0
N_ACTIVE_THREADS = 5
N_LAST_MESSAGES_IN_THREAD = 15
N_RECENT_MESSAGES = 20

DIALOGUE_DISENTANGLEMENT_SYSTEM_PROMPT = """You are an expert dialogue disentanglement AI. Your task is to route a target message to the correct existing conversation thread.

### INSTRUCTIONS
1. Read the ACTIVE THREADS, the TARGET MESSAGE, and the FUTURE CONTEXT.
2. Determine which active thread the target message logically belongs to.
3. CRITICAL: Pay close attention to the time elapsed between messages (e.g., indicated as "| +30s"). Short time gaps often indicate a continuous conversation flow, while large gaps might suggest a new topic. Use the future context to resolve ambiguities.
4. If the target message logically continues an active thread, output its exact Thread ID.
5. If the target message starts a completely new topic or does not fit ANY of the provided threads, output 0.
6. STRICT RULE: Output ONLY a single integer representing the ID. Do not add any text, reasoning, markdown formatting, or punctuation.

### EXAMPLES

--- Example 1 ---
Input:
<Thread ID="1">
Recent Messages:
- [2026-04-30 17:15:00] Alice: Are we still going hiking this Saturday?
- [2026-04-30 17:16:00 | +1m] Charlie: Yes, weather looks perfect.
- [2026-04-30 17:20:00 | +4m] Bob: I'll bring the tent.
</Thread>
<Thread ID="2">
Summary: Missing dog leash.
Recent Messages:
- [2026-04-30 17:45:00] Bob: Has anyone seen the dog's leash?
- [2026-04-30 17:46:00 | +1m] Alice: Check the garage, I left it there.
- [2026-04-30 17:50:00 | +4m] Bob: Found it, thanks!
</Thread>
<Thread ID="3">
Summary: Discussing dinner plans.
Recent Messages:
- [2026-04-30 18:00:00] Alice: What should we eat tonight?
- [2026-04-30 18:01:00 | +1m] Bob: Let's get pizza.
- [2026-04-30 18:01:45 | +45s] Charlie: I had pizza yesterday. How about sushi?
- [2026-04-30 18:02:15 | +30s] Alice: Sushi sounds great to me.
- [2026-04-30 18:03:00 | +45s] Bob: Any specific place in mind?
</Thread>
Target Message:
[2026-04-30 18:03:20 | +20s] Charlie: That new place on 5th avenue is supposed to be good.
Future Context:
- [2026-04-30 18:04:00 | +40s] Alice: Oh, Sakura Sushi?
- [2026-04-30 18:04:15 | +15s] Charlie: Yeah exactly.
- [2026-04-30 18:05:00 | +45s] Bob: Works for me, what time?
- [2026-04-30 18:05:30 | +30s] Alice: Let's aim for 7 PM.
- [2026-04-30 18:06:00 | +30s] Charlie: Perfect, I'll make a reservation.
Output:
number:3

--- Example 2 ---
Input:
<Thread ID="1">
Summary: Project deadline.
Recent Messages:
- [2026-04-30 09:00:00] Charlie: Is the report ready?
- [2026-04-30 09:05:00 | +5m] Alice: Almost, just formatting the charts.
- [2026-04-30 09:06:00 | +1m] Charlie: Great, client needs it by 10.
- [2026-04-30 09:08:00 | +2m] Alice: Understood.
- [2026-04-30 09:15:00 | +7m] Alice: Sent it to your email.
</Thread>
<Thread ID="2">
Summary: Server issues.
Recent Messages:
- [2026-04-30 09:02:00] Bob: The main server is down again.
- [2026-04-30 09:03:00 | +1m] Eve: I'm checking the logs now.
- [2026-04-30 09:04:30 | +1m30s] Bob: Getting a 502 Bad Gateway.
- [2026-04-30 09:06:00 | +1m30s] Eve: Looks like the database connection dropped.
- [2026-04-30 09:10:00 | +4m] Bob: Let me know when it's back up.
</Thread>
<Thread ID="3">
Summary: Office supplies.
Recent Messages:
- [2026-04-30 09:20:00] Alice: We are out of printer paper.
- [2026-04-30 09:22:00 | +2m] Dave: I'll order some more today.
- [2026-04-30 09:25:00 | +3m] Eve: Can you order black pens too?
- [2026-04-30 09:30:00 | +5m] Dave: Added to the list.
</Thread>
Target Message:
[2026-04-30 09:35:00 | +5m] Dave: By the way, did anyone see my car keys? I think I left them in the meeting room.
Future Context:
- [2026-04-30 09:36:00 | +1m] Eve: Try checking the kitchen table.
- [2026-04-30 09:36:45 | +45s] Dave: Not there, just checked.
- [2026-04-30 09:38:00 | +1m15s] Alice: I saw some keys near the whiteboard in Room A.
- [2026-04-30 09:39:00 | +1m] Dave: Oh, let me go look.
- [2026-04-30 09:42:00 | +3m] Dave: Found them! Thanks Alice.
Output:
number:0

--- Example 3 ---
Input:
<Thread ID="1">
Summary: UI design updates.
Recent Messages:
- [2026-04-30 13:30:00] Sarah: The new logo SVGs are in the drive.
- [2026-04-30 13:35:00 | +5m] John: Got them, I'll update the navbar.
- [2026-04-30 13:40:00 | +5m] Mike: Make sure the padding is 16px.
- [2026-04-30 13:42:00 | +2m] John: Will do.
</Thread>
<Thread ID="2">
Summary: Code review and auth module.
Recent Messages:
- [2026-04-30 13:50:00] John: I'm finishing up the auth module.
- [2026-04-30 13:52:00 | +2m] Mike: Did you fix the token refresh bug?
- [2026-04-30 13:55:00 | +3m] John: Yeah, that was just a typo in the header.
- [2026-04-30 13:58:00 | +3m] Mike: Cool, push it when ready.
- [2026-04-30 14:00:00 | +2m] John: I'll push the code in 5 minutes.
</Thread>
<Thread ID="3">
Summary: Lunch coffee order.
Recent Messages:
- [2026-04-30 14:05:00] Mike: Anyone want coffee? I'm going downstairs.
- [2026-04-30 14:06:00 | +1m] Sarah: Yes please! Flat white.
- [2026-04-30 14:08:00 | +2m] Mike: Noted, be back in 15.
</Thread>
Target Message:
[2026-04-30 14:10:00 | +2m] John: Done, please review PR #402.
Future Context:
- [2026-04-30 14:12:00 | +2m] Mike: Looking at it now.
- [2026-04-30 14:15:00 | +3m] Mike: Line 45, shouldn't this be an async call?
- [2026-04-30 14:16:30 | +1m30s] John: Ah good catch, let me update it.
- [2026-04-30 14:18:00 | +1m30s] John: Updated.
- [2026-04-30 14:20:00 | +2m] Mike: Approved and merged.
Output:
number:2
"""
