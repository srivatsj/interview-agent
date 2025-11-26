"""Pytest configuration for orchestrator tests."""

import sys
from pathlib import Path

# Add interview_orchestrator to path
orchestrator_root = Path(__file__).parent.parent
sys.path.insert(0, str(orchestrator_root))
