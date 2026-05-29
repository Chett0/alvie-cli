from ast import arg
from enum import Enum
from pydantic import BaseModel

from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from validators import FileExtensionValidator, DirectoryValidator, IntValidator

class InputType(Enum):
    FILENAME = "filename"
    DIRECTORY = "directory"
    CHOICE = "choice"
    BOOLEAN = "boolean"
    INT = "int"

class Validation(BaseModel):
    must_exist: bool = True

class Argument(BaseModel):
    description: str
    flag: str
    type: InputType
    extension : str | None = None
    validation: Validation | None = None
    values : list[str] | None = None
    default: str | None = None
    required: bool = False

    def select_value(self) -> str:
        message : str = f"{self.description} {'(required)' if self.required else '(optional)'}:"
        
        if self.type == InputType.FILENAME:
            if self.extension and not self.extension.startswith("."):
                self.extension = f".{self.extension}"
            
            must_exists = self.validation.must_exist if self.validation else True

            file : str = FilePathPrompt(
                message=message,
                default=self.default,
                validate=FileExtensionValidator(
                    expected_extension=self.extension,
                    must_exists=must_exists
                )
            ).execute()

            return file
        
        if self.type == InputType.DIRECTORY:
            must_exists = self.validation.must_exist if self.validation else True

            directory : str = FilePathPrompt(
                message=message,
                default=self.default,
                validate=DirectoryValidator(
                    must_exists=must_exists
                )
            ).execute()

            return directory
        
        if self.type == InputType.CHOICE:
            if not self.values:
                raise ValueError(f"Argument {self.flag} is of type choice but no values were provided.")
            
            choices = [Choice(value=value, name=value) for value in self.values]

            selected_choice : str = ListPrompt(
                message=message,
                choices=choices
            ).execute()

            return selected_choice
        
        if self.type == InputType.BOOLEAN:
            selected_boolean : str = ListPrompt(
                message=message,
                choices=[
                    Choice(value="true", name="Yes"), 
                    Choice(value="false", name="No")
                ]
            ).execute()

            return selected_boolean
        
        if self.type == InputType.INT:
            selected_int : str = InputPrompt(
                message=message,
                default=self.default,
                validate=IntValidator()
            ).execute()

            return selected_int
        
        else:
            raise ValueError(f"Argument {self.flag} has unknown type {self.type}.")

class Command(BaseModel):
    name: str
    description: str
    file: str
    args: list[Argument] = []