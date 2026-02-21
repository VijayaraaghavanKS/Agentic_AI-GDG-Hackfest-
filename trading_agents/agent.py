"""Root ADK agent -- coordinates regime, scanner, trade, and portfolio sub-agents."""

from google.adk.agents import Agent

from trading_agents.config import GEMINI_MODEL
from trading_agents.portfolio_agent import portfolio_agent
from trading_agents.regime_agent import regime_agent
from trading_agents.scanner_agent import scanner_agent
from trading_agents.trade_agent import trade_agent


root_agent = Agent(
    name="trading_assistant",
    model=GEMINI_MODEL,
    description=(
        "Regime-aware Indian stock market paper-trading assistant. "
        "Coordinates regime analysis, stock scanning, trade execution, "
        "and portfolio management using live NSE data."
    ),
    instruction=(
        "You are an Indian stock market paper-trading assistant. "
        "You help users analyze the market, find trade opportunities, "
        "execute paper trades, and manage their portfolio.\n\n"
        "WORKFLOW:\n"
        "1. When asked about market conditions, delegate to regime_analyst.\n"
        "2. When asked to find stocks or scan, delegate to stock_scanner.\n"
        "3. When asked to trade, delegate to trade_executor.\n"
        "4. When asked about portfolio, delegate to portfolio_manager.\n"
        "5. For a full scan-to-trade flow, first check regime, then scan, then trade.\n\n"
        "RULES:\n"
        "- This is PAPER TRADING only. Never claim real money is at risk.\n"
        "- Always show data source and timestamp in responses.\n"
        "- Format Indian currency as INR with commas (e.g., INR 10,00,000).\n"
        "- Be concise, data-driven, and explain your reasoning."
    ),
    sub_agents=[regime_agent, scanner_agent, trade_agent, portfolio_agent],
)
