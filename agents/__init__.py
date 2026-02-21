"""
agents/__init__.py

Exports the four Regime-Aware pipeline agents:
    from agents import sentiment_agent, bull_agent, bear_agent, cio_agent
"""

from .sentiment_agent import sentiment_agent
from .bull_agent import bull_agent
from .bear_agent import bear_agent
from .cio_agent import cio_agent

__all__ = ["sentiment_agent", "bull_agent", "bear_agent", "cio_agent"]
