"""
pipeline/ – Public orchestration interface
==========================================
Exports the `Orchestrator` facade used by CLI/UI entrypoints.

Usage:
    from pipeline import Orchestrator
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]
