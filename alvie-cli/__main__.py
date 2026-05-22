from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.validator import PathValidator
from InquirerPy.inquirer import filepath

from utils import get_alvie_code_path, get_commands, run_alvie


def choose_command(alvie_path: Path):

    done = False
    args = []
    commands = get_commands().values()

    while not done:
        choice = ListPrompt(
            message="What do you want to do:",
            choices=[
                Choice(
                    value=command,
                    name=command["name"]
                ) for command in commands
            ]
        ).execute()

        if choice["name"] == "Exit":
            return
        
        done, args = choose_args(choice)
        
    run_alvie(alvie_path, "learn", args)


def choose_args(command: dict) -> tuple[bool, list[str]]:

    args = []
    config_args = command["args"]
    required_args = [arg for arg in config_args if arg["required"]]
    optional_args = [arg for arg in config_args if not arg["required"]]

    for arg in required_args:
        
        type = arg.get("type", None)
        if not type: raise ValueError(f"Argument {arg['flag']} does not have a type specified.")
        
        if type in ["filename", "directory"]:
                        
            value = filepath(
                message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
                default = arg['default'],
                # TODO: add check on specific file extension
                # TODO: add custom validator for new dirs / files
                # validate=PathValidator(
                    # is_file=(type == "filename"), 
                    # is_dir=(type == "directory"),
                    # message="Input is not a valid file path"),
            ).execute()
            
        elif type == "choice":
            
            value = ListPrompt(
                message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
                choices=arg["values"]
            ).execute()
            
        if not value: raise ValueError(f"Argument {arg['flag']} is required but no value was provided.")
        
        args.extend([f"{arg['flag']}", value])

    choice = ListPrompt(
        message="Do you want to provide optional arguments?",
        choices=[arg["description"] for arg in optional_args] + ["Done", "Back"],
    ).execute()
    
    # TODO: manage optional arguments
    
    # /home/alvie/spec-lib/example/enclave.etdl requires explicit secret in '?'
    args.extend(["--secret", "0"])
    
    
    
    return True, args

def main():

    try:
        alvie_path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)

    choose_command(alvie_path)


if __name__ == "__main__":
    main()