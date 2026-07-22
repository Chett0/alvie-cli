from io import TextIOWrapper
from pathlib import Path
import os
import shutil
from .runner import AlvieExecution


def merge_tmp_file(
        merged: TextIOWrapper,
        temp_path: Path | None
):
    """Merge a temporary file chunk output into the final output file."""
    if not temp_path or not temp_path.exists():
        return
    with temp_path.open("r", encoding="utf-8") as chunk:
        shutil.copyfileobj(chunk, merged)
    merged.write("\n")


def remove_tmp_files(
        executions: list[AlvieExecution]
) -> None:
    """Remove temporary files created during parallel execution."""
    for execution in executions:
        temp_path = execution.output_path
        if temp_path and temp_path.exists():
            try:
                os.unlink(temp_path)
            except OSError:
                pass