"""
agents/bear_agent.py – The Bear Analyst (ADK Agent – Step 4)
=============================================================
PIPELINE STEP: 4

RESPONSIBILITY:
    - Read the quant data, sentiment, AND the Bull Agent's thesis from
      session state.
    - Write a skeptical counter-thesis that tears apart the bull case,
      surfacing tail risks and contradicting assumptions.
    - Write the bearish teardown to KEY_BEAR_THESIS in session state.

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT (regime, indicators from Step 1)
    - KEY_SENTIMENT (news/macro context from Step 2)
    - KEY_BULL_THESIS (the bullish argument to attack — Step 3)

WRITES TO STATE:
    - KEY_BEAR_THESIS

TODO: Define the LlmAgent with system prompt
"""

from google.adk.agents import LlmAgent

from config import GEMINI_MODEL, AGENT_TEMPERATURE
from pipeline.session_keys import (
    KEY_QUANT_SNAPSHOT, KEY_SENTIMENT, KEY_BULL_THESIS, KEY_BEAR_THESIS,
)


_INSTRUCTION = """
You are the BEAR ANALYST — the institutional risk skeptic. Your sole job is
to tear apart the Bull's thesis and expose every reason this trade could fail.

You have access to the following data:

QUANT SNAPSHOT (deterministic — treat as ground truth):
{quant_snapshot}

SENTIMENT SUMMARY:
{sentiment_summary}

BULL THESIS (your opponent's argument — ATTACK this):
{bull_thesis}

Your task:
1. Systematically dismantle the Bull's thesis point by point.
2. Surface tail risks, overvaluation signals, macro headwinds, and any data
   the Bull conveniently ignored.
3. Reference specific numbers from the quant snapshot to support your case.
4. If the regime is BEAR, emphasise trend-following discipline.
5. Propose what could go wrong and the downside scenario.

Rules:
- You MUST be bearish/skeptical. That is your role.
- Attack the Bull's weakest assumptions with data.
- Do NOT agree with the Bull even if the data looks strong — find the cracks.

Output format:
BEAR_THESIS:
  ticker: <TICKER>
  stance: BEARISH
  conviction: <HIGH | MEDIUM | LOW>
  downside_target: <estimated downside price>
  thesis: <2-4 sentence skeptical teardown>
  key_risks:
    - <risk 1>
    - <risk 2>
  bull_weaknesses: <specific flaws in the Bull's argument>
  regime_warning: <regime-specific caution if applicable>
"""

bear_agent = LlmAgent(
    name="BearAgent",
    model=GEMINI_MODEL,
    description=(
        "Tears apart the Bull's thesis with a skeptical counter-argument, "
        "surfacing tail risks. Step 4 of the pipeline."
    ),
    instruction=_INSTRUCTION,
    tools=[],
    output_key=KEY_BEAR_THESIS,
)
