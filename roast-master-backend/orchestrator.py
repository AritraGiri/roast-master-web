"""
orchestrator.py — Roast Master AI: Multi-Agent Pipeline
=========================================================
Defines three specialised roast agents that run in PARALLEL via asyncio,
then feeds all their outputs to a Judge Agent that synthesises the final burn.

Providers used (via litellm):
  • The Observer   → Groq        (llama-3.3-70b-versatile)
  • The Sarcastic  → Gemini      (gemini-2.0-flash)
  • The Brutal     → OpenRouter  (meta-llama/llama-3.3-70b-instruct)
  • The Judge      → Groq        (llama-3.3-70b-versatile)
    ↳ Swap any of these for any litellm-supported model string.
Install dependencies:
    pip install litellm asyncio

API key setup — see the os.environ block below.
"""

import os
import asyncio
import litellm

from dotenv import load_dotenv
load_dotenv()
# ══════════════════════════════════════════════════════════════════════════════
# MODEL CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
MODEL_OBSERVER  = "groq/llama-3.3-70b-versatile"
MODEL_SARCASTIC = "gemini/gemini-2.0-flash"
MODEL_BRUTAL    = "openrouter/meta-llama/llama-3.3-70b-instruct"
MODEL_JUDGE     = "groq/llama-3.3-70b-versatile"

# ══════════════════════════════════════════════════════════════════════════════
# API KEY CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
# Set these as environment variables before running the server, e.g.:
#
#   export GROQ_API_KEY="gsk_..."
#   export GEMINI_API_KEY="AIza..."
#   export OPENROUTER_API_KEY="sk-or-..."
#
# Or place them in a .env file and load with `python-dotenv`.
# NEVER hard-code keys here — this file may end up in version control.

os.environ["GROQ_API_KEY"]       = os.environ.get("GROQ_API_KEY", "")        # https://console.groq.com
os.environ["GEMINI_API_KEY"]     = os.environ.get("GEMINI_API_KEY", "")      # https://aistudio.google.com/apikey
os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")  # https://openrouter.ai/keys

# Optional: set ANTHROPIC_API_KEY here if you swap the Judge to claude-*
# os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")  # https://console.anthropic.com

# Suppress litellm's verbose success logs — keep stderr clean
litellm.set_verbose = False


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT BUILDERS (VERSION: THE MULTI-LAYERED BURN)
# ══════════════════════════════════════════════════════════════════════════════

def build_observer_prompt(profile: dict) -> str:
    """The Observer: Jimmy Carr Style (Logical contradiction)"""
    return (
        f"You are 'The Observer' acting as Jimmy Carr. Intel: {profile['name']}, {profile['major']}, {profile['tech']}, \"{profile['hotTake']}\". "
        "Delivery: 2-3 deadpan, logical sentences. Focus on the sad reality that their tech stack is their only personality trait. "
        "Connect their 'Hot Take' to their lack of a social life using cold, mathematical logic. 😐📉 "
        "No exclamation marks. Output ONLY the observation."
    )

def build_sarcastic_prompt(profile: dict) -> str:
    """The Sarcastic: Nikki Glaser Style (Mocking the vibe)"""
    return (
        f"You are 'The Sarcastic' acting as Nikki Glaser. Intel: {profile['name']}, \"{profile['hotTake']}\", {profile['tech']}. "
        "Delivery: 2-3 drippingly ironic, eye-rolling sentences. "
        "Treat them like a basic NPC who thinks they are a 'main character' because they use C++. 🙄💅 "
        "Roast their 'Hot Take' as being the most predictable thing you've ever heard. Output ONLY the retort."
    )

def build_brutal_prompt(profile: dict) -> str:
    """The Brutal: Jeff Ross Style (Personal and situational)"""
    return (
        f"You are 'The Brutal' acting as Jeff Ross. Intel: {profile['name']}, {profile['major']}, {profile['tech']}, \"{profile['hotTake']}\". "
        "Delivery: A heavy-hitting burn under 80 words (2-3 sentences). "
        "Use 'You look like...' or 'You're the type of person who...' comparisons. "
        "Go for their lack of charisma and their embarrassing choice of major. Don't just roast the code; roast the coder. 🔥💀 "
        "Output ONLY the burn."
    )

def build_judge_prompt(profile: dict, heat_level: int) -> str:
    """The Judge: Anthony Jeselnik Style (The dark final synthesis)"""
    if heat_level <= 33:
        severity = "Clever social jab. No vulgarity. 😏"
    elif heat_level <= 66:
        severity = "Pointed and personal. Target their pride and their 'Hot Take'. 3 sentences max. 😈⚖️"
    else:
        severity = "Total soul destruction. 2-3 devastating sentences. Leave no survivors. ⚰️🔥"

    return (
        f"You are the Lead Roast Master acting as Anthony Jeselnik. Target: {profile['name']}. "
        "MANDATE: Combine the agents' inputs into a cohesive 2-3 sentence paragraph. "
        "Balance the roast: 50% about their personality/hot-take and 50% about their tech/major. "
        f"Heat Level: {heat_level}/100 ({severity}). "
        "Style: Arrogant, dark, and perfectly timed. Include emojis that suit the reply. "
        "No intro, no labels. Output ONLY the final blow."
    )

#═══════════════════════════════════════════════════════════════════════
# INDIVIDUAL AGENT CALLERS  (async, each isolated for fault tolerance)
# ══════════════════════════════════════════════════════════════════════════════

async def call_observer(query: str, profile: dict) -> str:
    """
    Calls The Observer (Groq / Llama 3.3 70B).
    Returns the agent's output string, or a fallback on failure.
    """
    try:
        response = await litellm.acompletion(
            model    = MODEL_OBSERVER,
            messages = [
                {"role": "system", "content": build_observer_prompt(profile)},
                {"role": "user",   "content": query},
            ],
            max_tokens  = 120,
            temperature = 0.8,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        # Log the failure but don't crash — the Judge can still work without this agent
        print(f"[Observer] Model call failed: {exc}")
        return f"[Observer offline — still judging {profile['name']} silently]"


async def call_sarcastic(query: str, profile: dict) -> str:
    """
    Calls The Sarcastic (Gemini 2.0 Flash).
    Returns the agent's output string, or a fallback on failure.
    """
    try:
        response = await litellm.acompletion(
            model    = MODEL_SARCASTIC,
            messages = [
                {"role": "system", "content": build_sarcastic_prompt(profile)},
                {"role": "user",   "content": query},
            ],
            max_tokens  = 120,
            temperature = 0.9,   # slightly higher for more unpredictable sarcasm
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        print(f"[Sarcastic] Model call failed: {exc}")
        return f"[Sarcastic agent is too exhausted by {profile['name']}'s take to respond]"


async def call_brutal(query: str, profile: dict) -> str:
    """
    Calls The Brutal (OpenRouter / Llama 3.3 70B Instruct).
    Returns the agent's output string, or a fallback on failure.
    """
    try:
        response = await litellm.acompletion(
            model    = MODEL_BRUTAL,
            messages = [
                {"role": "system", "content": build_brutal_prompt(profile)},
                {"role": "user",   "content": query},
            ],
            max_tokens  = 120,
            temperature = 0.85,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        print(f"[Brutal] Model call failed: {exc}")
        return f"[Brutal agent has been temporarily stunned by {profile['name']}'s audacity]"


async def call_judge(
    query         : str,
    profile       : dict,
    heat_level    : int,
    observer_out  : str,
    sarcastic_out : str,
    brutal_out    : str,
) -> str:
    """
    Calls The Judge (Groq / Llama 3.3 70B) with all three agent outputs assembled
    into a single user message so the Judge can synthesise them.

    The Judge always runs AFTER the three agents (sequential, not parallel) because
    it depends on their outputs.
    """
    # Assemble the three agent outputs as a structured prompt for the Judge
    agent_summary = (
        f"User said: \"{query}\"\n\n"
        f"=== Agent Reports ===\n"
        f"[The Observer]  : {observer_out}\n"
        f"[The Sarcastic] : {sarcastic_out}\n"
        f"[The Brutal]    : {brutal_out}\n\n"
        f"Now deliver the final synthesised roast."
    )

    try:
        response = await litellm.acompletion(
            model    = MODEL_JUDGE,
            messages = [
                {"role": "system", "content": build_judge_prompt(profile, heat_level)},
                {"role": "user",   "content": agent_summary},
            ],
            max_tokens  = 200,
            temperature = 0.75,  # slightly lower for a more controlled, polished output
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        print(f"[Judge] Model call failed: {exc}")
        # Last-resort fallback: stitch the best available agent output together
        available = [o for o in [observer_out, sarcastic_out, brutal_out]
                     if "[" not in o]  # skip fallback placeholder strings
        if available:
            return " ".join(available[:2])  # combine up to 2 real outputs
        return (
            "The AI is currently laughing too hard at your profile to respond. Try again."
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def run_multi_agent_pipeline(
    query       : str,
    user_profile: dict,
    heat_level  : int,
) -> dict:
    """
    Orchestrates the full multi-agent roast pipeline.

    Flow:
        1. asyncio.gather() fires The Observer, The Sarcastic, and The Brutal
           IN PARALLEL — all three model calls happen simultaneously.
        2. Once all three resolve (or fail gracefully), their outputs are passed
           to The Judge which runs sequentially and returns the final roast.
        3. Returns a structured dict ready for app.py to forward to the frontend.

    Args:
        query        : The user's latest chat message.
        user_profile : dict — { name, major, tech, hotTake }
        heat_level   : int 10–100, controls Judge severity.

    Returns:
        {
            "roast"         : str,         # final synthesised burn from the Judge
            "agent_previews": [str, str, str]  # [observer, sarcastic, brutal] previews
        }
    """

    # ── Step 1: Run three agents in PARALLEL ──────────────────────────────
    # asyncio.gather schedules all three coroutines concurrently.
    # return_exceptions=True means a crash in one agent won't cancel the others.
    observer_out, sarcastic_out, brutal_out = await asyncio.gather(
        call_observer (query, user_profile),
        call_sarcastic(query, user_profile),
        call_brutal   (query, user_profile),
        return_exceptions=False,  # individual try/except blocks handle errors above
    )

    # ── Step 2: Run the Judge (sequential — needs all three outputs) ──────
    final_roast = await call_judge(
        query,
        user_profile,
        heat_level,
        observer_out,
        sarcastic_out,
        brutal_out,
    )

    # ── Step 3: Build agent preview snippets (first ~6 words + ellipsis) ──
    # These are shown in the three agent status boxes on the frontend.
    def make_preview(text: str) -> str:
        words = text.split()
        return " ".join(words[:6]) + ("…" if len(words) > 6 else "")

    return {
        "roast": final_roast,
        "agent_previews": [
            make_preview(observer_out),
            make_preview(sarcastic_out),
            make_preview(brutal_out),
        ],
    }
