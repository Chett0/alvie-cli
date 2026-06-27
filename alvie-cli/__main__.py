import argparse
import sys
from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from entities import Entity, build_entity
from validators import FileExtensionValidator
from executions import (
    execute,
    build_commands,
    get_config_command,
    validate_config_command,
)
from output import run_alvie
from utils import get_alvie_code_path
from banner import print_banner


def json_output_path(value: str) -> Path:
    """Validate a JSON output"""
    try:
        FileExtensionValidator.json_file_validator().validate(Document(value))
    except ValidationError as error:
        raise argparse.ArgumentTypeError(error.message)
    return Path(value)


def run_non_interactive(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="alvie-cli",
        description="Interface for the Alvie analysis tool. "
                    "Run with no arguments for the interactive mode, "
                    "or pass a saved configuration file to execute it directly.",
    )
    parser.add_argument(
        "configs",
        nargs="+",
        help="Paths to saved command configurations (JSON) to execute."
             "Default sequential execution"
    )
    parser.add_argument(
        "-r", "--raw-output",
        action="store_true",
        help="Stream the raw standard output instead of the parsed/formatted output",
    )
    parser.add_argument(
        "-o", "--output",
        # nargs="+" #TODO handle multiple outputs file for multiple configurations,
        default=None,
        type=json_output_path,
        help="Path to a json file where the output will be saved (default: stdout)"
    )
    parser.add_argument(
        "--njobs",
        type=int,
        default=1,
        help="Number of configurations to run in parallel (default: 1)",
    )

    namespace = parser.parse_args(argv)

    if namespace.njobs < 1:
        parser.error("--njobs must be a positive integer")

    if not namespace.configs:
        parser.error("No configuration files provided")
    config_paths = [Path(config) for config in namespace.configs]
    for config_path in config_paths:
        if not config_path.is_file():
            parser.error(f"Configuration file not found: {config_path}")

    build_commands()

    jobs: list[tuple[Path, str, list[str]]] = []
    for config_path in config_paths:
        try:
            config_command = get_config_command(config_path)
            command = validate_config_command(config_command)
        except ValueError as error:
            parser.error(f"{config_path}: {error}")

        jobs.append((
            config_path, 
            command.executable, 
            config_command.args
        ))

    alvie_path = get_alvie_code_path()

    # sequential execution
    if namespace.njobs == 1:
        for job in jobs:
            _, executable, args = job
            run_alvie(
                alvie_path=alvie_path,
                executable_name=executable,
                args=args,
                is_raw_output=namespace.raw_output,
                json_output_path=namespace.output
            )
    # TODO parallel execution


def run_interactive() -> None:
    print_banner()

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
    try:
        if len(sys.argv) == 1:
            run_interactive()
        else:
            run_non_interactive(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
