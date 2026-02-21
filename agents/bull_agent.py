"""
agents/bull_agent.py – The Bull Analyst (ADK Agent – Step 3)
=============================================================
PIPELINE STEP: 3

RESPONSIBILITY:
    - Read the quant regime data and sentiment summary from session state.
    - Construct the most aggressive, evidence-backed bullish thesis it can
      defend.
    - Write the bullish thesis to KEY_BULL_THESIS in session state.

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT (regime, indicators from Step 1)
    - KEY_SENTIMENT (news/macro context from Step 2)

WRITES TO STATE:
    - KEY_BULL_THESIS

TODO: Define the LlmAgent with system prompt
"""

from google.adk.agents import LlmAgent

from config import GEMINI_MODEL, AGENT_TEMPERATURE
from pipeline.session_keys import KEY_QUANT_SNAPSHOT, KEY_SENTIMENT, KEY_BULL_THESIS


_INSTRUCTION = """
You are the BULL ANALYST on an institutional trading desk. Your job is to
make the strongest possible case for buying this stock RIGHT NOW.

You have access to the following data:

QUANT SNAPSHOT (deterministic — treat as ground truth):
{quant_snapshot}

SENTIMENT SUMMARY:
{sentiment_summary}

Your task:
1. Build the most compelling, evidence-backed BULLISH thesis you can defend.
2. Reference specific numbers from the quant snapshot (regime, DMA, RSI, ATR).
3. Incorporate the sentiment data to strengthen your case.
4. Propose an entry price, target price, and your conviction level.

Rules:
- You MUST be bullish. That is your role. Argue aggressively.
- Acknowledge risks briefly, then explain why they are priced in or manageable.
- Ground every claim in the data provided. No hallucinated price targets.

Output format:
BULL_THESIS:
  ticker: <TICKER>
  stance: BULLISH
  conviction: <HIGH | MEDIUM | LOW>
  entry: <proposed entry price>
  target: <proposed target price>
  thesis: <2-4 sentence aggressive bullish argument>
  key_catalysts:
    - <catalyst 1>
    - <catalyst 2>
  acknowledged_risks: <brief risk acknowledgement>
"""

bull_agent = LlmAgent(
    name="BullAgent",
    model=GEMINI_MODEL,
    description=(
        "Constructs an aggressive, evidence-backed bullish thesis using "
        "quant data and sentiment. Step 3 of the pipeline."
    ),
    instruction=_INSTRUCTION,
    tools=[],
    output_key=KEY_BULL_THESIS,
)
