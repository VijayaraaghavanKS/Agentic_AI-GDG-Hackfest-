"""
tests/test_agents_and_utils.py – Tests for agents/ structure and utils/helpers.py
===================================================================================
Covers: agents/agent.py structure, utils/helpers.py, config.py constants
"""

from __future__ import annotations

import json
import logging

import pytest


# ──────────────────────────────────────────────────────────────
# 1–9. agents/agent.py structure tests
# ──────────────────────────────────────────────────────────────

class TestRootAgentStructure:

    def test_root_agent_exists_and_importable(self):
        """root_agent exists and is importable."""
        from agents.agent import root_agent

        assert root_agent is not None

    def test_root_agent_name(self):
        """root_agent.name == 'RegimeAwareTradingPipeline'."""
        from agents.agent import root_agent

        assert root_agent.name == "RegimeAwareTradingPipeline"

    def test_eight_sub_agents_in_correct_order(self):
        """8 sub-agents in correct order."""
        from agents.agent import root_agent

        subs = root_agent.sub_agents
        assert len(subs) == 8

    def test_sub_agent_names(self):
        """Sub-agent names match expected list."""
        from agents.agent import root_agent

        expected = [
            "MarketContextAgent",
            "QuantToolAgent",
            "QuantAgent",
            "SentimentAgent",
            "BullAgent",
            "BearAgent",
            "CIOAgent",
            "RiskToolAgent",
        ]
        actual = [a.name for a in root_agent.sub_agents]
        assert actual == expected

    def test_quant_tool_agent_temperature_zero(self):
        """QuantToolAgent has temperature=0.0."""
        from agents.agent import root_agent

        quant_tool_agent = root_agent.sub_agents[1]
        assert quant_tool_agent.name == "QuantToolAgent"
        config = quant_tool_agent.generate_content_config
        assert config is not None
        assert config.temperature == pytest.approx(0.0)

    def test_quant_tool_agent_has_quant_engine_tool(self):
        """QuantToolAgent has tools containing quant_engine_tool."""
        from agents.agent import root_agent
        from tools.quant_tool import quant_engine_tool

        quant_tool_agent = root_agent.sub_agents[1]
        assert quant_tool_agent.name == "QuantToolAgent"
        assert quant_tool_agent.tools is not None
        # Check that one of the tools is quant_engine_tool
        tool_funcs = [t for t in quant_tool_agent.tools if t is quant_engine_tool]
        assert len(tool_funcs) >= 1, "quant_engine_tool not found in QuantToolAgent.tools"

    def test_cio_agent_has_no_tools(self):
        """CIOAgent has no tools."""
        from agents.agent import root_agent

        cio_agent = root_agent.sub_agents[6]
        assert cio_agent.name == "CIOAgent"
        assert cio_agent.tools is None or len(cio_agent.tools) == 0

    def test_sentiment_agent_has_google_search(self):
        """SentimentAgent has tools containing google_search."""
        from agents.agent import root_agent
        from google.adk.tools import google_search

        sentiment_agent = root_agent.sub_agents[3]
        assert sentiment_agent.name == "SentimentAgent"
        assert sentiment_agent.tools is not None
        tool_funcs = [t for t in sentiment_agent.tools if t is google_search]
        assert len(tool_funcs) >= 1, "google_search not found in SentimentAgent.tools"

    def test_risk_tool_agent_has_risk_enforcement_tool(self):
        """RiskToolAgent has tools containing risk_enforcement_tool."""
        from agents.agent import root_agent
        from tools.risk_tool import risk_enforcement_tool

        risk_tool_agent = root_agent.sub_agents[7]
        assert risk_tool_agent.name == "RiskToolAgent"
        assert risk_tool_agent.tools is not None
        tool_funcs = [t for t in risk_tool_agent.tools if t is risk_enforcement_tool]
        assert len(tool_funcs) >= 1, "risk_enforcement_tool not found in RiskToolAgent.tools"


# ──────────────────────────────────────────────────────────────
# 10–26. utils/helpers.py
# ──────────────────────────────────────────────────────────────

class TestSetupLogger:

    def test_returns_logger_instance(self):
        """setup_logger returns logging.Logger instance."""
        from utils.helpers import setup_logger

        logger = setup_logger()
        assert isinstance(logger, logging.Logger)

    def test_custom_name(self):
        """setup_logger with custom name."""
        from utils.helpers import setup_logger

        logger = setup_logger(name="my_test_logger_custom")
        assert logger.name == "my_test_logger_custom"


class TestPrettyPrintState:

    def test_doesnt_raise(self, capsys):
        """pretty_print_state doesn't raise (prints to stdout)."""
        from utils.helpers import pretty_print_state

        state = {"key1": "value1", "key2": {"nested": True}}
        pretty_print_state(state)  # should not raise
        captured = capsys.readouterr()
        assert "SHARED WHITEBOARD" in captured.out


class TestParseCioJson:

    def test_valid_json_string(self):
        """parse_cio_json with valid JSON string → dict."""
        from utils.helpers import parse_cio_json

        raw = json.dumps({"ticker": "RELIANCE.NS", "action": "BUY"})
        result = parse_cio_json(raw)
        assert isinstance(result, dict)
        assert result["ticker"] == "RELIANCE.NS"

    def test_strips_markdown_fences(self):
        """parse_cio_json with markdown fences → strips and parses."""
        from utils.helpers import parse_cio_json

        raw = "```\n" + json.dumps({"action": "SELL"}) + "\n```"
        result = parse_cio_json(raw)
        assert isinstance(result, dict)
        assert result["action"] == "SELL"

    def test_json_with_language_tag(self):
        """parse_cio_json with ```json ... ``` → works."""
        from utils.helpers import parse_cio_json

        raw = "```json\n" + json.dumps({"ticker": "TCS.NS"}) + "\n```"
        result = parse_cio_json(raw)
        assert isinstance(result, dict)
        assert result["ticker"] == "TCS.NS"

    def test_embedded_json_in_text(self):
        """parse_cio_json with embedded JSON in text → extracts it."""
        from utils.helpers import parse_cio_json

        raw = 'Here is my recommendation: {"ticker": "INFY.NS", "action": "HOLD"} end.'
        result = parse_cio_json(raw)
        assert isinstance(result, dict)
        assert result["ticker"] == "INFY.NS"

    def test_garbage_returns_none(self):
        """parse_cio_json with garbage → None."""
        from utils.helpers import parse_cio_json

        assert parse_cio_json("total garbage no json here") is None

    def test_empty_string_returns_none(self):
        """parse_cio_json with empty string → None."""
        from utils.helpers import parse_cio_json

        assert parse_cio_json("") is None


class TestFormatCurrencyInr:

    def test_basic_value(self):
        """format_currency_inr(1234.56) → '₹1,234.56'."""
        from utils.helpers import format_currency_inr

        assert format_currency_inr(1234.56) == "₹1,234.56"

    def test_zero(self):
        """format_currency_inr(0) → '₹0.00'."""
        from utils.helpers import format_currency_inr

        assert format_currency_inr(0) == "₹0.00"

    def test_large_value(self):
        """format_currency_inr(1000000) → '₹1,000,000.00'."""
        from utils.helpers import format_currency_inr

        assert format_currency_inr(1000000) == "₹1,000,000.00"


class TestGetActionColour:

    def test_buy_green(self):
        """get_action_colour('BUY') → '#00C853'."""
        from utils.helpers import get_action_colour

        assert get_action_colour("BUY") == "#00C853"

    def test_sell_red(self):
        """get_action_colour('SELL') → '#D50000'."""
        from utils.helpers import get_action_colour

        assert get_action_colour("SELL") == "#D50000"

    def test_hold_amber(self):
        """get_action_colour('HOLD') → '#FF6D00'."""
        from utils.helpers import get_action_colour

        assert get_action_colour("HOLD") == "#FF6D00"


class TestFormatRiskReward:

    def test_basic_ratio(self):
        """format_risk_reward(2.5) → '1:2.50'."""
        from utils.helpers import format_risk_reward

        assert format_risk_reward(2.5) == "1:2.50"

    def test_zero_ratio(self):
        """format_risk_reward(0) → '1:0.00'."""
        from utils.helpers import format_risk_reward

        assert format_risk_reward(0) == "1:0.00"


# ──────────────────────────────────────────────────────────────
# 27–34. config.py constants
# ──────────────────────────────────────────────────────────────

class TestConfigConstants:

    def test_gemini_model_non_empty_string(self):
        """GEMINI_MODEL is a non-empty string."""
        from config import GEMINI_MODEL

        assert isinstance(GEMINI_MODEL, str)
        assert len(GEMINI_MODEL) > 0

    def test_max_risk_pct(self):
        """MAX_RISK_PCT == 0.01."""
        from config import MAX_RISK_PCT

        assert MAX_RISK_PCT == pytest.approx(0.01)

    def test_atr_stop_multiplier(self):
        """ATR_STOP_MULTIPLIER == 1.5."""
        from config import ATR_STOP_MULTIPLIER

        assert ATR_STOP_MULTIPLIER == pytest.approx(1.5)

    def test_min_risk_reward(self):
        """MIN_RISK_REWARD == 2.0."""
        from config import MIN_RISK_REWARD

        assert MIN_RISK_REWARD == pytest.approx(2.0)

    def test_default_portfolio_equity(self):
        """DEFAULT_PORTFOLIO_EQUITY == 1_000_000.0."""
        from config import DEFAULT_PORTFOLIO_EQUITY

        assert DEFAULT_PORTFOLIO_EQUITY == pytest.approx(1_000_000.0)

    def test_watch_list_has_at_least_10_tickers(self):
        """WATCH_LIST has at least 10 tickers."""
        from config import WATCH_LIST

        assert isinstance(WATCH_LIST, list)
        assert len(WATCH_LIST) >= 10

    def test_default_period(self):
        """DEFAULT_PERIOD == '1y'."""
        from config import DEFAULT_PERIOD

        assert DEFAULT_PERIOD == "1y"

    def test_default_interval(self):
        """DEFAULT_INTERVAL == '1d'."""
        from config import DEFAULT_INTERVAL

        assert DEFAULT_INTERVAL == "1d"
