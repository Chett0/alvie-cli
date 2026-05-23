from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from utils import get_alvie_code_path, get_commands, run_alvie
from input_selectors import select_file, select_directory, select_choice, select_boolean, select_int

types_selector = {
    "filename" : select_file,
    "directory" : select_directory,
    "choice" : select_choice,
    "boolean" : select_boolean,
    "int" : select_int
}

def choose_command(alvie_path: Path):

    done = False
    args = []
    commands = get_commands().values()

    # TODO manage commands with classes as the instructions

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

def get_arg_value(arg: dict) -> str:
    type = arg.get("type", None)
    if not type: raise ValueError(f"Argument {arg['flag']} does not have a type specified.")
    
    selector = types_selector.get(type, None)
    if not selector: raise ValueError(f"Argument {arg['flag']} has unknown type {type}.")

    value = selector(arg)
    if not value: raise ValueError(f"Argument {arg['flag']} is required but no value was provided.")

    return value

def choose_args(command: dict) -> tuple[bool, list[str]]:

    args = []
    config_args = command["args"]

    required_args = []
    optional_args = []

    for arg in config_args:
        if arg.get("required"):
            required_args.append(arg)
        else:
            optional_args.append(arg)
            

    for arg in required_args:
        value = get_arg_value(arg)
        args.extend([f"{arg['flag']}", value])


    while optional_args:

        optional_choices = [Choice(value=arg, name=arg["description"]) for arg in optional_args]
        arg = ListPrompt(
            message="Do you want to provide optional arguments?",
            choices=optional_choices + [Choice(value="Done", name="done"), Choice(value="Back", name="back")]
        ).execute()

        if arg == "Done":
            break
        if arg == "Back":
            return False, []
        else:
            value = get_arg_value(arg)
            args.extend([f"{arg['flag']}", value])
            optional_args.remove(arg)
    
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
