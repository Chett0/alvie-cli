import os
import json
from pathlib import Path
from dotenv import load_dotenv

from InquirerPy.base.control import Choice

load_dotenv()

DONE_CHOICE : Choice = Choice(value="Done", name="[✓] Done")
BACK_CHOICE : Choice = Choice(value="Back", name="[←] Back")
HELP_CHOICE : Choice = Choice(value="Help", name="[?] Help")
SHOW_CHOICE : Choice = Choice(value="Show", name="[~] Show")

def is_done(value) -> bool:
    return value == DONE_CHOICE.value

def is_back(value) -> bool:
    return value == BACK_CHOICE.value

def is_help(value) -> bool:
    return value == HELP_CHOICE.value

def is_show(value) -> bool:
    return value == SHOW_CHOICE.value

def get_alvie_code_path() -> Path:
    alvie_code_path = os.environ["ALVIE_CODE_PATH"]

    if not alvie_code_path:
        raise EnvironmentError(
            "ALVIE_CODE_PATH environment variable is not set. Please set it to the path of the Alvie codebase."
        )

    return Path(alvie_code_path).expanduser().resolve()

def load_commands():

    commands_path = Path(__file__).resolve().parent.parent / "config" / "commands.json"
    with commands_path.open("r") as file:
        return json.load(file)

def load_args():

    args_path = Path(__file__).resolve().parent.parent / "config" / "args.json"
    with args_path.open("r") as file:
        return json.load(file)

def load_instructions():

    instructions_path = Path(__file__).resolve().parent.parent / "config" / "instructions.json"
    with instructions_path.open("r") as file:
        return json.load(file)
    
def load_combinators():
    
    combinators_path = Path(__file__).resolve().parent.parent / "config" / "combinators.json"
    with combinators_path.open("r") as file:
        return json.load(file)
    
def load_output_symbols():
    
    output_symbols_path = Path(__file__).resolve().parent.parent / "config" / "output_symbols.json"
    with output_symbols_path.open("r") as file:
        return json.load(file)