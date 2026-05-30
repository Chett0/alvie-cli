from commands import Command, Argument
from utils import BACK_CHOICE, DONE_CHOICE, get_alvie_code_path, is_back, is_done, load_commands, run_alvie

from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt

from entities import build_choices


def get_commands() -> list[Command]:
    raw_commands : list = load_commands()
    if not raw_commands:
        raise RuntimeError("No commands found. Please check the configuration.")
    commands : list[Command] = [
        Command.model_validate(raw_command) 
        for raw_command in raw_commands
    ]

    return commands

def choose_args(command: Command) -> tuple[bool, list[str]]:

    chosen_args : list[str] = []
    
    required_args : list[Argument] = [arg for arg in command.args if arg.required]
    optional_args : list[Argument] = [arg for arg in command.args if not arg.required]

    for arg in required_args: collect_arg(arg, chosen_args)
    
    while optional_args:
        optional_choices : list[Choice] = [Choice(value=arg, name=arg.description) for arg in optional_args]
        arg: Argument = ListPrompt(
            message="Do you want to provide optional arguments?",
            choices= optional_choices + [BACK_CHOICE, DONE_CHOICE]
        ).execute()

        if is_done(arg):
            break
        if is_back(arg):
            return False, []
        else:
            collect_arg(arg, chosen_args)
            optional_args.remove(arg)
    
    return True, chosen_args

def collect_arg(arg: Argument, args: list[str]):
    value = arg.select_value()
    if isinstance(value, bool):
        if value:
            args.extend([f"{arg.flag}"])
    else: 
        args.extend([f"{arg.flag}", value])

def execute() -> None:
    try:
        alvie_path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)
    
    commands : list[Command] = get_commands()

    choices : list[Choice] = build_choices(
        items=commands,
        extra_choices=[DONE_CHOICE]
    )

    while True:
        action = FuzzyPrompt(
            message="What do you want to do:",
            choices=choices
        ).execute()

        if is_done(action):
            return
        
        execute, args = choose_args(action)
        if execute:
            run_alvie(alvie_path, "learn", args)
            return

    