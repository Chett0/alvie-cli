import argparse
import sys
from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from entities import Entity, build_entity
from executions import (
    execute,
    build_commands,
    get_config_command,
    validate_config_command,
)
from output import run_alvie
from utils import get_alvie_code_path


def run_non_interactive(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="alvie-cli",
        description="Interface for the Alvie analysis tool. "
                    "Run with no arguments for the interactive mode, "
                    "or pass a saved configuration file to execute it directly.",
    )
    parser.add_argument(
        "config",
        help="Path to a saved command configuration (JSON) to execute",
    )
    parser.add_argument(
        "-s", "--std-output",
        action="store_true",
        help="Stream the raw standard output instead of the parsed/formatted output",
    )
    namespace = parser.parse_args(argv)

    config_path = Path(namespace.config)
    if not config_path.is_file():
        parser.error(f"Configuration file not found: {config_path}")

    build_commands()

    try:
        config_command = get_config_command(config_path)
        command = validate_config_command(config_command)
    except ValueError as error:
        parser.error(str(error))

    run_alvie(
        alvie_path=get_alvie_code_path(),
        executable_name=command.executable,
        args=config_command.args,
        std_output=namespace.std_output,
    )


def run_interactive() -> None:
    print("\nWelcome to the Alvie CLI!\n")

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
            execute()
        elif choice == "exit":
            return
        else:
            build_entity(choice)


def main() -> None:
    if len(sys.argv) == 1:
        run_interactive()
    else:
        run_non_interactive(sys.argv[1:])


if __name__ == "__main__":
    main()
