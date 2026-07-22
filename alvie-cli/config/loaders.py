import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

def _load(filename: str):
    with (CONFIG_DIR / filename).open("r") as file:
        return json.load(file)

def load_commands():
    return _load("commands.json")

def load_args():
    return _load("args.json")

def load_instructions():
    return _load("instructions.json")

def load_combinators():
    return _load("combinators.json")

def load_output_symbols():
    return _load("output_symbols.json")
