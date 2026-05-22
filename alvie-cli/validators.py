from pathlib import Path

from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.document import Document

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