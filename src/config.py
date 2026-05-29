import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

def load_config() -> dict:
    with open(ROOT / "config.json") as f:
        return json.load(f)
