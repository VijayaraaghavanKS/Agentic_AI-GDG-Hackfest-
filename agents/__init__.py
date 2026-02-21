"""
agents/__init__.py

Exports the three core agents so any file can import them as:
    from agents import researcher, analyst, decision_maker
"""

from .researcher import researcher_agent
from .analyst import analyst_agent
from .decision_maker import decision_agent

__all__ = ["researcher_agent", "analyst_agent", "decision_agent"]
