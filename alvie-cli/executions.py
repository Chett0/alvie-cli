import json
from pathlib import Path

from commands import Command, Argument, ConfigCommand
from utils import BACK_CHOICE, DONE_CHOICE, get_alvie_code_path, is_back, is_done, load_commands
from output import run_alvie

from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.filepath import FilePathPrompt

from entities import build_choices
from validators import FileExtensionValidator


def get_commands() -> list[Command]:
    raw_commands : list = load_commands()
    if not raw_commands:
        raise RuntimeError("No commands found. Please check the configuration.")
    commands : list[Command] = [
        Command.model_validate(raw_command) 
        for raw_command in raw_commands
    ]

    return commands


def get_config_command(
        file_path : Path
) -> ConfigCommand:
    # TODO handle exceptions using validators
    with file_path.open("r") as file:
        config_command = json.load(file)

    if not config_command:
        raise RuntimeError("No configuration command found.")
    
    command = ConfigCommand.model_validate(config_command)

    return command



def select_args(command: Command) -> tuple[bool, list[str]]:

    chosen_args : list[str] = []
    
    required_args : list[Argument] = [arg for arg in command.args if arg.required]
    optional_args : list[Argument] = [arg for arg in command.args if not arg.required]

    for arg in required_args: collect_arg(arg, chosen_args)
    
    while optional_args:
        # I use index rather than the args because inquirerPy does a deep copy of choices
        optional_choices : list[Choice] = [
            Choice(value=index, name=arg.description) 
            for index, arg in enumerate(optional_args)
        ] 

        arg = ListPrompt(
            message="Do you want to provide optional arguments?",
            choices= optional_choices + [BACK_CHOICE, DONE_CHOICE]
        ).execute()

        if is_done(arg):
            break
        if is_back(arg):
            return False, []
        else:
            argument : Argument = optional_args[arg]
            collect_arg(argument, chosen_args)
            optional_args.remove(argument)
    
    return True, chosen_args


def collect_arg(arg: Argument, args: list[str]):
    value = arg.select_value()
    if isinstance(value, bool):
        if value:
            args.extend([f"{arg.flag}"])
    else: 
        args.extend([f"{arg.flag}", value])


def select_config() -> tuple[bool, ConfigCommand]:
    file : str = FilePathPrompt(
            message="Select the configuration file for the command:",
            default="/home/alvie/alvie-cli/config/config.json",
            validate=FileExtensionValidator(
                expected_extension=".json",
                must_exists=True
            )
        ).execute()

    file_path : Path = Path(file)
    config_command : ConfigCommand = get_config_command(file_path)

    return True, config_command


def execute() -> None:
    try:
        alvie_path : Path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)
    
    commands : list[Command] = get_commands()

    choices : list[Choice] = build_choices(
        items=commands,
        extra_choices=[DONE_CHOICE]
    )

    
    config : bool = ConfirmPrompt(
        message="Do you want to use a configuration?",
        default=True,
    ).execute()

    if not config:
        action = FuzzyPrompt(
            message="What do you want to do:",
            choices=choices
        ).execute()
    
        if is_done(action):
            return

        executable = action.executable
        execute, args = select_args(action)

        dump_config : bool = ConfirmPrompt(
            message="Do you want to save this configuration?",
            default=True,
        ).execute()

        if dump_config:
            config_path : str = FilePathPrompt(
                    message="Select the path where to save the configuration:",
                    default="/home/alvie/alvie-cli/config/config.json",
                    validate=FileExtensionValidator(
                        expected_extension=".json",
                        must_exists=False
                    )
                ).execute()

            with open(config_path, "w") as config_file:
                json.dump({
                    "name" : action.name,
                    "executable" : executable,
                    "args": args
                }, config_file, indent=2)

    else:
        execute, command = select_config()
        args = command.args
        executable = command.executable

    if execute:
        std_output: bool = ConfirmPrompt(
            message="Do you want to see the standard output of the command?",
            default=True,
        ).execute()

        run_alvie(
            alvie_path=alvie_path, 
            executable_name=executable, 
            args=args,
            std_output=std_output
        )

    