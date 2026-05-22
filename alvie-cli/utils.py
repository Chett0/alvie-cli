import os
from pathlib import Path
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()

def get_alvie_code_path() -> Path:
    # alvie_code_path = os.getenv("ALVIE_CODE_PATH")
    alvie_code_path = os.environ["ALVIE_CODE_PATH"]

    if not alvie_code_path:
        raise EnvironmentError(
            "ALVIE_CODE_PATH environment variable is not set. Please set it to the path of the Alvie codebase."
        )

    return Path(alvie_code_path).expanduser().resolve()


def run_alvie(
        alvie_path: Path, 
        executable_name : str,
        args: list[str]
    ) -> None:

    # execute if file .ml is modified
    # subprocess.run(["dune", "build"],
    #                 cwd=alvie_path,
    #                 check=True
    #                 )
    
    exe = f"{alvie_path}/_build/default/bin/{executable_name}.exe"
    print(f"Running {exe} with arguments")
    for i in range(len(args)//2):
        print(f"{args[2*i]}: {args[2*i+1]}")
    print()
    subprocess.run([exe, *args], cwd=alvie_path, check=True)

def get_commands():

    commands_path = Path(__file__).resolve().parent.parent / "commands" / "commands.json"
    with commands_path.open("r") as file:
        return json.load(file)
