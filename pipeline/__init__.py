"""
pipeline/ – ADK Orchestration Layer
=====================================
Wires the full sequential ADK pipeline and manages the shared whiteboard.

Usage:
    from pipeline import Orchestrator
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]
