from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.input import InputPrompt

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

    args = command["args"]
    required_args = [arg for arg in args if arg["required"]]
    optional_args = [arg for arg in args if not arg["required"]]

    for arg in required_args:
        choice = ListPrompt(
            message=f"{arg['description']} (required):",
            choices=[f"Enter {arg['flag']} value", "Back"],
        ).execute()

        if choice == "Back":
            return False, []
        elif choice == f"Enter {arg['flag']} value":
            if arg.get("values", None):
                value = ListPrompt(
                    message=f"Select value for {arg['flag']}:",
                    choices=arg["values"]
                ).execute()
            else:
                value = InputPrompt(message=f"Enter value for {arg['flag']}:").execute()
            print(f"Received {arg['flag']} value: {value}")
            args.append(f"{arg['flag']}")
            args.append(value)

    choice = ListPrompt(
        message="Do you want to provide optional arguments?",
        choices=[arg["description"] for arg in optional_args] + ["Done", "Back"],
    ).execute()

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