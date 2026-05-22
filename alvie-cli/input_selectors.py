from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from validators import FileExtensionValidator, DirectoryValidator, IntValidator


def select_file(arg: dict) -> str:
    expected_extension = arg.get("extension")
    if expected_extension and not expected_extension.startswith("."):
        expected_extension = f".{expected_extension}"

    must_exists = True
    validation = arg.get("validation")
    if validation:
        must_exists = validation.get("must_exists", True)

    value = FilePathPrompt(
        message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
        default=arg['default'],
        validate=FileExtensionValidator(
            expected_extension=expected_extension,
            must_exists=must_exists
        )
    ).execute()

    return value


def select_directory(arg: dict) -> str:
    must_exists = True
    validation = arg.get("validation")
    if validation:
        must_exists = validation.get("must_exists", True)

    value = FilePathPrompt(
        message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
        default=arg['default'],
        validate=DirectoryValidator(
            must_exists=must_exists
        )
    ).execute()

    return value


def select_choice(arg: dict) -> str:
    value = ListPrompt(
        message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
        choices=arg["values"]
    ).execute()

    return value


def select_boolean(arg: dict) -> str:
    value = ListPrompt(
        message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
        choices=[Choice(value="true", name="Yes"), Choice(value="false", name="No")]
    ).execute()

    return value


def select_int(arg: dict) -> str:
    value = InputPrompt(
        message=f"{arg['description']} {'(required)' if arg['required'] else '(optional)'}:",
        default=arg['default'],
        validate=IntValidator()
    ).execute()

    return value
