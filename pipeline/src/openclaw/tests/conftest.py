"""Pytest configuration — ensure src/ is in the Python path."""
import sys
from pathlib import Path

# Add pipeline/src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
