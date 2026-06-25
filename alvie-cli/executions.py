import json
import os
from pathlib import Path

from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.confirm import ConfirmPrompt
from InquirerPy.prompts.filepath import FilePathPrompt

from prompt_toolkit.validation import ValidationError

from commands import Command, Argument, ConfigCommand
from utils import DONE_CHOICE, get_alvie_code_path, is_done, load_args, load_commands, validate_save_path
from output import run_alvie
from entities import build_choices
from validators import FileExtensionValidator
from flows import Flow, StepOutput, StepResult, CommandState, create_prompt


ALVIE_PATH = get_alvie_code_path()
commands_map : dict[str, Command] = {}


def build_commands() -> dict[str, Command]:
    global commands_map

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

    commands_map = {
        command.name : command
        for command in commands
    }

    return commands_map


def get_config_command(
        file_path : Path
) -> ConfigCommand:
    with file_path.open("r") as file:
        config_command = json.load(file)

    if not config_command:
        raise RuntimeError("No configuration command found.")
    
    command = ConfigCommand.model_validate(config_command)

    return command


def validate_config_command(config_command: ConfigCommand) -> Command:
    """
    Validate a loaded configuration against the known command/argument definitions.

    Returns the matched Command. Raises ValueError if the command is unknown or any flag/value pairing is inconsistent.
    """
    command : Command | None = commands_map.get(config_command.name)
    if not command:
        raise ValueError(f"Command {config_command.name} not found in the configuration.")

    pending_arg : Argument | None = None
    for token in config_command.args:
        if token.startswith("--"):
            if pending_arg:
                raise ValueError(f"Argument {pending_arg.flag} has no value in the configuration.")

            command_arg : Argument | None = command.get_arg_by_flag(token)
            if not command_arg:
                raise ValueError(f"Argument {token} not found in command {config_command.name}.")

            pending_arg = command_arg if command_arg.requires_value() else None
        else:
            if not pending_arg:
                raise ValueError(f"Value {token} has no corresponding argument flag in the configuration.")

            try:
                pending_arg.validate_value(token)
            except ValidationError as error:
                raise ValueError(
                    f"Validation error for argument {pending_arg.flag}: {error.message}"
                ) from error

            pending_arg = None

    if pending_arg:
        raise ValueError(f"Argument {pending_arg.flag} has no value in the configuration.")

    return command



def select_args(state: CommandState) -> StepOutput:
    # TODO add the opporunity to going back on args selection
    if not state.name:
        print("No command selected.")
        return StepOutput.back()

    command : Command | None = commands_map.get(state.name)
    if not command:
        print(f"Command {state.name} not found in the configuration.")
        return StepOutput.back()

    chosen_args : list[str] = []
    
    required_args : list[Argument] = [arg for arg in command.args if arg.required]
    optional_args : list[Argument] = [arg for arg in command.args if not arg.required]

    for arg in required_args: 
        result = collect_arg(arg, chosen_args)
        if result is StepResult.BACK:
            return StepOutput.back()
    
    while optional_args:
        # I use index rather than the args because inquirerPy does a deep copy of choices
        optional_choices : list[Choice] = [
            Choice(value=index, name=arg.description) 
            for index, arg in enumerate(optional_args)
        ] 

        arg = create_prompt(
            ListPrompt,
            message="Do you want to provide optional arguments?",
            choices= optional_choices + [DONE_CHOICE]
        ).execute()

        if arg is StepResult.BACK:
            return StepOutput.back()

        if is_done(arg):
            break

        else:
            argument : Argument = optional_args[arg]
            result = collect_arg(argument, chosen_args)
            if result is StepResult.BACK:
                return StepOutput.back()
            optional_args.remove(argument)
    
    state.args = chosen_args
    return StepOutput.next("select_dump")


def collect_arg(arg: Argument, args: list[str]) -> StepResult | None:
    value = arg.select_value()
    if value is StepResult.BACK:
        return StepResult.BACK
    if isinstance(value, bool):
        if value:
            args.extend([f"{arg.flag}"])
    else: 
        args.extend([f"{arg.flag}", value])


def select_config(state: CommandState) -> StepOutput:
    file = create_prompt(
            FilePathPrompt,
            message="Select the configuration file for the command:",
            default="/home/alvie/alvie-cli/presets/config.json",
            validate=FileExtensionValidator(
                expected_extension=".json",
                must_exists=True
            )
        ).execute()

    if file is StepResult.BACK:
        return StepOutput.back()

    file_path : Path = Path(file)
    config_command : ConfigCommand = get_config_command(file_path)

    try:
        validate_config_command(config_command)
    except ValueError as error:
        print(error)
        return StepOutput.stay()

    state.args = config_command.args
    state.executable = config_command.executable
    state.name = config_command.name

    return StepOutput.next("execute_alvie")


def branch_config(state: CommandState) -> StepOutput:
    config = create_prompt(
        ConfirmPrompt,
        allow_back=True,
        message="Do you want to use a configuration?",
        default=True
    ).execute()

    if config is StepResult.BACK:
        return StepOutput.back()

    if config:
        return StepOutput.next("select_config")
    else:
        return StepOutput.next("select_command")


def execute_alvie(state: CommandState) -> StepOutput:
    if not state.executable:
        return StepOutput.back()

    std_output: bool = create_prompt(
            ConfirmPrompt,
            allow_back=True,
            message="Do you want to see the standard output of the command?",
            default=True,
        ).execute()

    if std_output is StepResult.BACK:
        return StepOutput.back()

    run_alvie(
        alvie_path=ALVIE_PATH, 
        executable_name=state.executable, 
        args=state.args,
        std_output=std_output
    )

    return StepOutput.next()


def select_command(state: CommandState) -> StepOutput:
    choices : list[Choice] = build_choices(
        items=list(commands_map.values()),
        extra_choices=[DONE_CHOICE]
    )

    action = create_prompt(
            FuzzyPrompt,
            allow_back=True,
            message="Select a command to execute:",
            choices=choices
    ).execute()

    if action is StepResult.BACK:
        return StepOutput.back()

    if is_done(action):
        return StepOutput.next()
    
    state.name = action.name
    state.executable = action.executable

    return StepOutput.next("select_args")


def select_dump(state: CommandState) -> StepOutput:
    dump_config : bool = create_prompt(
            ConfirmPrompt,
            allow_back=True,
            message="Do you want to save this configuration?",
            default=True,
        ).execute()

    if dump_config is StepResult.BACK:
        return StepOutput.back()
    
    if dump_config:
        return StepOutput.next(next_step="select_dump_path")
    else:
        return StepOutput.next(next_step="execute_alvie")


def select_dump_path(state: CommandState) -> StepOutput:
    WORKING_PATH = os.environ.get("WORKING_PATH", "/home/alvie/alvie-cli")
            
    config_path = validate_save_path(
        message="Select the path where to save the configuration:",
        default_path=f"{WORKING_PATH}/presets/config.json",
        validator=FileExtensionValidator(
            expected_extension=".json",
            must_exists=False
        )
    )
    
    if config_path:
        with open(config_path, "w") as config_file:
            json.dump({
                "name" : state.name,
                "executable" : state.executable,
                "args": state.args
            }, config_file, indent=2)
        print(f"Configuration saved to {config_path}")

    return StepOutput.next(next_step="execute_alvie")


def execute() -> None:
    build_commands()

    flow = Flow(
        steps={
            "branch_config": branch_config,
            "select_config": select_config,
            "select_command": select_command,
            "select_args": select_args,
            "select_dump": select_dump,
            "select_dump_path": select_dump_path,
            "execute_alvie": execute_alvie,
        },
        root="branch_config",
        initial_state=CommandState()
    )
    flow.run()

    
