from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.input import InputPrompt

from learn import learn
from utils import get_alvie_code_path, run_executable

executable = [
    {
        "name" : "Learn",
        "description" : "Learn a Mealy machine model",
        "file" : "learn.exe"
    },
    {
        "name" : "Fa",
        "description" : "Find flow-analysis (NI) violations between two models",
        "file" : "fa.exe"
    },
    {
        "name" : "Exit"
    }
]

def execution_type(alvie_code_path: Path):

    done = False
    args = []

    while not done:
        choice = ListPrompt(
            message="What do you want to do:",
            choices=[exe["name"] for exe in executable],
        ).execute()

        if choice == "Learn":
            done, args = learn()
        # Add more execution types
        elif choice == "Exit":
            return

    run_executable(alvie_code_path, "learn", args)



def main():

    try:
        alvie_code_path = get_alvie_code_path()
    except EnvironmentError as error:
        print(error)
        raise SystemExit(1)

    execution_type(alvie_code_path)




if __name__ == "__main__":
    main()