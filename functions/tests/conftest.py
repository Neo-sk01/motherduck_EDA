import sys
from pathlib import Path

# Make 'functions/run-pipeline' importable as a package-relative path for tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-pipeline"))
