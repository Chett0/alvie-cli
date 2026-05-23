from pathlib import Path

from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.document import Document

from instructions import Operand

class FileExtensionValidator(Validator):

    def __init__(self, expected_extension: str | None = None, must_exists: bool = True):
        self.expected_extension = expected_extension
        self.must_exists = must_exists

    def validate(self, document : Document) -> None:
        path = Path(document.text)
        if self.must_exists and not path.is_file():
            raise ValidationError(
                message="Input is not a valid file path",
                cursor_position=document.cursor_position
            )
        if self.expected_extension and path.suffix != self.expected_extension:
            raise ValidationError(
                message=f"Input file must have extension {self.expected_extension}",
                cursor_position=document.cursor_position
            ) 
        
class DirectoryValidator(Validator):

    def __init__(self, must_exists: bool = True):
        self.must_exists = must_exists

    def validate(self, document : Document) -> None:
        path = Path(document.text)
        if self.must_exists and not path.is_dir():
            raise ValidationError(
                message="Input is not a valid directory path",
                cursor_position=document.cursor_position
            )
        
class IntValidator(Validator):

    def __init__(self):
        pass

    def validate(self, document : Document) -> None:
        if not document.text.isdigit():
            raise ValidationError(
                message="Input must be an integer",
                cursor_position=document.cursor_position
            )
        

class ParameterValidator(Validator):

    def __init__(self, operand_types: list[Operand]):
        self.operand_types = operand_types

    def validate(self, document: Document) -> None:
        
        for operand_type in self.operand_types:
            if operand_type.is_valid(document.text):
                return
            
        raise ValidationError(
            message=f"Input does not match any of the expected operand types: {', '.join([operand_type.value for operand_type in self.operand_types])}",
            cursor_position=document.cursor_position
        )