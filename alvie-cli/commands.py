from enum import Enum
from unittest import case
from typing_extensions import Self
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from prompt_toolkit.validation import Validator
from prompt_toolkit.document import Document

from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice


from instructions import BaseChoice
from validators import FileExtensionValidator, DirectoryValidator, IntValidator, ValuesValidator

class InputType(Enum):
    FILENAME = "filename"
    DIRECTORY = "directory"
    CHOICE = "choice"
    BOOLEAN = "boolean"
    INT = "int"

class Validation(BaseModel):
    must_exists: bool = True

class Argument(BaseModel):
    description: str
    flag: str
    type: InputType
    extension : str | None = None
    validation: Validation | None = None
    values : list[str] | None = None
    default: str | None = None
    required: bool = False

    _validator: Validator | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def populate_validator(self) -> Self:

        match self.type:
            case InputType.FILENAME:
                if self.extension and not self.extension.startswith("."):
                    self.extension = f".{self.extension}"
                
                must_exists = self.validation.must_exists if self.validation else True
                self._validator = FileExtensionValidator(
                    expected_extension=self.extension,
                    must_exists=must_exists
                )
            case InputType.DIRECTORY:
                must_exists = self.validation.must_exists if self.validation else True
                self._validator = DirectoryValidator(
                    must_exists=must_exists
                )

            case InputType.INT:
                self._validator = IntValidator()

            case InputType.CHOICE:
                if not self.values:
                    raise ValueError(f"Argument {self.flag} is of type choice but no values were provided.")

                self._validator = ValuesValidator(
                    values=self.values 
                )

        return self

    def select_value(self) -> str | bool:
        message : str = f"{self.description} {'(required)' if self.required else '(optional)'}:"
        
        match self.type:
            case InputType.FILENAME | InputType.DIRECTORY:
                path : str = FilePathPrompt(
                    message=message,
                    default=self.default,
                    validate=self._validator
                ).execute()

                return path
        
            case InputType.CHOICE:
                if not self.values:
                    raise ValueError(f"Argument {self.flag} is of type choice but no values were provided.")
                
                choices = [Choice(value=value, name=value) for value in self.values]

                selected_choice : str = ListPrompt(
                    message=message,
                    choices=choices
                ).execute()

                return selected_choice
        
            case InputType.BOOLEAN:
                selected_boolean : bool = ListPrompt(
                    message=message,
                    choices=[
                        Choice(value=True, name="Yes"), 
                        Choice(value=False, name="No")
                    ]
                ).execute()

                return selected_boolean
        
            case InputType.INT:
                selected_int : str = InputPrompt(
                    message=message,
                    default=self.default,
                    validate=self._validator
                ).execute()

                return selected_int
        
            case _:
                raise ValueError(f"Argument {self.flag} has unknown type {self.type}.")

    def validate_value(self, value: str) -> None:
        if self._validator:
            document = Document(text=value)
            self._validator.validate(document=document)
    
    def needs_value(self) -> bool:
        return self.type != InputType.BOOLEAN


class Command(BaseChoice):
    executable: str
    args: list[Argument] = Field(default_factory=list)
    
    def get_arg_by_flag(self, flag: str) -> Argument | None:
        for arg in self.args:
            if arg.flag == flag:
                return arg
            
        return None


class ConfigCommand(BaseModel):
    name: str
    executable: str
    args : list[str]