import os
from pathlib import Path
import subprocess
from dotenv import load_dotenv

load_dotenv()

def get_alvie_code_path() -> Path:
    alvie_code_path = os.getenv("ALVIE_CODE_PATH")

    if not alvie_code_path:
        raise EnvironmentError(
            "ALVIE_CODE_PATH environment variable is not set. Please set it to the path of the Alvie codebase."
        )

    return Path(alvie_code_path).expanduser().resolve()


def run_executable(
        alvie_code_path: Path, 
        executable_name : str,
        args: list[str]):

    subprocess.run("dune build",
                    cwd=alvie_code_path,
                    check=True
                    )
    subprocess.run([f"{alvie_code_path}/_build/default/bin/{executable_name}.exe", *args])