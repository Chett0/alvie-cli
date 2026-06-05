import os
import json
from pathlib import Path
from dotenv import load_dotenv

from InquirerPy.base.control import Choice

load_dotenv()

DONE_CHOICE : Choice = Choice(value="Done", name="[✓] Done")
BACK_CHOICE : Choice = Choice(value="Back", name="[←] Back")
HELP_CHOICE : Choice = Choice(value="Help", name="[?] Help")
SHOW_CHOICE : Choice = Choice(value="Show", name="[~] Show")

def is_done(value) -> bool:
    return value == DONE_CHOICE.value

def is_back(value) -> bool:
    return value == BACK_CHOICE.value

def is_help(value) -> bool:
    return value == HELP_CHOICE.value

def is_show(value) -> bool:
    return value == SHOW_CHOICE.value

def get_alvie_code_path() -> Path:
    alvie_code_path = os.environ["ALVIE_CODE_PATH"]

    if not alvie_code_path:
        raise EnvironmentError(
            "ALVIE_CODE_PATH environment variable is not set. Please set it to the path of the Alvie codebase."
        )

    return Path(alvie_code_path).expanduser().resolve()


# def run_alvie(
#         alvie_path: Path, 
#         executable_name : str,
#         args: list[str]
#     ) -> None:

#     # execute if file .ml is modified
#     # subprocess.run(["dune", "build"],
#     #                 cwd=alvie_path,
#     #                 check=True
#     #                 )
    
#     exe = f"{alvie_path}/_build/default/bin/{executable_name}.exe"
#     print(f"\nRunning {exe} with arguments")
#     for i in range(len(args)//2):
#         print(f"{args[2*i]}: {args[2*i+1]}")
#     print()
#     # subprocess.run([exe, *args], cwd=alvie_path, check=True)
    
#     process = subprocess.run(
#         [exe, *args],
#         cwd=alvie_path,
#         capture_output=True,
#         text=True,
#         check=True
#     )
    
#     # TODO define the actor using the color
#     res : str = strip_ansi(process.stdout)
#     hypotheses : list[str] = res.split("\n")
#     raw_symbols : dict = load_output_symbols()
#     input_symbols, output_symbols = raw_symbols["inputs"], raw_symbols["outputs"]
    
#     for i, line in enumerate(hypotheses):
#         raw_hypothesis = line.strip()
#         if raw_hypothesis:
#             hypothesis = parse_hypothesis(
#                 raw_hypothesis=raw_hypothesis, 
#                 i=i, 
#                 input_symbols=input_symbols,
#                 output_symbols=output_symbols,
#             )
#             print(hypothesis)  

#     print("Recap\n")
#     for symbol, data in output_symbols.items():
#         count = data.get("count", 0)
#         print(f"\t{data['description']} {symbol}: {count}") 

#     print("\n")        
            
    
# def parse_hypothesis(
#         raw_hypothesis: str, 
#         i : int,
#         input_symbols: dict,
#         output_symbols: dict
# ) -> str:
    
#     res = f"Hypothesis {i+1}:\n\n"
    
#     raw_runs : list[str] = raw_hypothesis.split(".")
    
#     for j, raw_run in enumerate(raw_runs):
#         if raw_run:
#             res += f"Run {j+1}:\n\n"
            
#             steps = re.findall(r'\[(.*?)\]', raw_run)
            
#             for step in steps:
#                 # Groups: [input output]
#                 match = re.match(r"^([A-Z_=]+)(.*)$", step)
                
#                 if match: 
#                     input, output = match.groups()
#                     input_symbol, output_symbol = input_symbols[input], output_symbols[output]
#                     output_symbol["count"] = output_symbol.get("count", 0) + 1
#                     res += f"\t{input_symbol['description']} ({input}) -> {output_symbol['description']} ({output})\n\n"

#     res += "\n\n"
#     return res

def load_commands():

    commands_path = Path(__file__).resolve().parent.parent / "config" / "commands.json"
    with commands_path.open("r") as file:
        return json.load(file)

def load_instructions():

    instructions_path = Path(__file__).resolve().parent.parent / "config" / "instructions.json"
    with instructions_path.open("r") as file:
        return json.load(file)
    
def load_combinators():
    
    combinators_path = Path(__file__).resolve().parent.parent / "config" / "combinators.json"
    with combinators_path.open("r") as file:
        return json.load(file)
    
def load_output_symbols():
    
    output_symbols_path = Path(__file__).resolve().parent.parent / "config" / "output_symbols.json"
    with output_symbols_path.open("r") as file:
        return json.load(file)