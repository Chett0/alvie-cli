from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from utils import BACK_CHOICE, DONE_CHOICE, get_alvie_code_path, get_commands, is_back, is_done, run_alvie
from input_selectors import select_file, select_directory, select_choice, select_boolean, select_int
from instructions import Entity
from entities import build_enclave, build_attacker

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

        optional_choices : list[Choice] = [Choice(value=arg, name=arg["description"]) for arg in optional_args]
        arg = ListPrompt(
            message="Do you want to provide optional arguments?",
            choices=optional_choices + [DONE_CHOICE, BACK_CHOICE]
        ).execute()

        if is_done(arg):
            break
        if is_back(arg):
            return False, []
        else:
            value = get_arg_value(arg)
            args.extend([f"{arg['flag']}", value])
            optional_args.remove(arg)
    
    # /home/alvie/spec-lib/example/enclave.etdl requires explicit secret in '?'
    args.extend(["--secret", "0"])
    
    return True, args

def excution():

    try:
        alvie_path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)

    choose_command(alvie_path)
    
def build(entity: Entity):
    if entity == Entity.ENCLAVE:
        build_enclave()
    elif entity == Entity.ATTACKER:
        build_attacker()

def main():

    print("Welcome to the Alvie CLI!\n")
    
    while True:
        choice = ListPrompt(
            message="What do you want to do:",
            choices=[
                Choice(value="execute", name="Execute a command") 
            ] + [
                Choice(value=entity, name=f"Build {entity.value}")
                for entity in Entity
            ] + [
                Choice(value="exit", name="Exit")
            ]
        ).execute()

        if choice == "execute":
            excution()
        elif choice == "exit":
            return
        else:
            build(choice)


if __name__ == "__main__":
    main()
