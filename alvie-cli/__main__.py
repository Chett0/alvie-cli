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
from output import AlvieExecution
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
    # Mapping outputs to multiple configurations.
    #
    # The current implementation accepts one path per configuration and pairs `-o out1.json out2.json ...`
    # them positionally (configs[i] -> output[i]). It is validated below so the
    # number of paths must match the number of configs, and each is passed to the
    # matching AlvieExecution as `json_output_path`.
    #
    # Alternatives considered (not implemented):
    #   1) Output directory + derived names: `-o DIR`, each file named after the
    #      config stem (e.g. <config>.json). Scales to any N and is race-free under
    #      parallel runs, but same-stem configs collide and it needs a directory check.
    #   2) Single aggregated JSON: one `-o results.json` collecting every run into one
    #      document keyed by config. Great for comparing configs, but executions must
    #      return their document and the caller writes once (collect-then-write under
    #      --njobs).
    #   3) Filename template: `-o "out/{name}_{index}.json"` with placeholders
    #      substituted per execution. Most flexible from one argument, but more surface
    #      to document and validate.
    parser.add_argument(
        "-o", "--output",
        nargs="+",
        default=None,
        type=json_output_path,
        help="Paths to json files where the output will be saved, one per "
             "configuration in the same order (default: stdout)"
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
    if namespace.output and len(namespace.output) != len(namespace.configs):
        parser.error("The number of output paths must match the number of configuration files")

    config_paths = [Path(config) for config in namespace.configs]
    for config_path in config_paths:
        if not config_path.is_file():
            parser.error(f"Configuration file not found: {config_path}")

    build_commands()

    alvie_path = get_alvie_code_path()

    executions: list[AlvieExecution] = []
    for i, config_path in enumerate(config_paths):
        try:
            config_command = get_config_command(config_path)
            command = validate_config_command(config_command)
        except ValueError as error:
            parser.error(f"{config_path}: {error}")

        executions.append(AlvieExecution(
            alvie_path=alvie_path,
            executable=command.executable,
            args=config_command.args,
            is_raw_output=namespace.raw_output,
            json_output_path=namespace.output[i],
        ))

    # sequential execution
    if namespace.njobs == 1:
        for execution in executions:
            execution.run()
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
