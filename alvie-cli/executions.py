import json
from pathlib import Path

from commands import Command, Argument, ConfigCommand
from utils import BACK_CHOICE, DONE_CHOICE, get_alvie_code_path, is_back, is_done, load_args, load_commands
from output import run_alvie

from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.filepath import FilePathPrompt

from entities import build_choices
from validators import FileExtensionValidator

dict_commands: dict[str, Command] = {}

def get_commands() -> list[Command]:
    
    raw_commands : list = load_commands()
    raw_args : dict[str, dict] = load_args()
    
    commands : list[Command] = []
    
    # Load effective args
    for raw_command in raw_commands:
        
        cmd = {key: value for key, value in raw_command.items() if key in {"name", "description", "executable"}}
        cmd["args"] = []
        
        for arg in raw_command.get("args", []):
            cmd_arg = {"flag": arg}
            cmd_arg.update(raw_args.get(arg, {}))
            cmd["args"].append(Argument.model_validate(cmd_arg))
            
        commands.append(Command.model_validate(cmd))

    if not commands:
        raise RuntimeError("No commands found. Please check the configuration.")

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


def select_config(dict_commands: dict[str, Command]) -> tuple[bool, ConfigCommand | None]:
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

    command : Command | None = dict_commands.get(config_command.name)
    if not command:
        print(f"Command {config_command.name} not found in the configuration.")
        return False, None
    
    previous_args : Argument | None = None
    for arg in config_command.args:
        if arg.startswith("--"):
            if previous_args:
                print(f"Argument {previous_args.flag} has no value in the configuration.")
                return False, None

            command_arg : Argument | None = command.get_arg_by_flag(arg)
            if not command_arg:
                print(f"Argument {arg} not found in command {config_command.name}.")
                return False, None
            
            if command_arg.needs_value():
                previous_args = command_arg
            else:
                previous_args = None
        else:
            if not previous_args:
                print(f"Value {arg} has no corresponding argument flag in the configuration.")
                return False, None
            
            try:
                previous_args.validate_value(arg)
            except Exception as error:
                print(f"Validation error for argument {previous_args.flag}: {error}")
                return False, None
            
            previous_args = None

    return True, config_command


def execute() -> None:
    global dict_commands

    try:
        alvie_path : Path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)
    
    if not dict_commands:
        commands : list[Command] = get_commands()
        dict_commands = {
            command.name : command
            for command in commands
        }
    else:
        commands = list(dict_commands.values())

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
        execute, command = select_config(dict_commands)
        if command is None:
            return
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

    