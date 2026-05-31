import subprocess
from pathlib import Path
from collections import Counter
import re

from utils import load_output_symbols

SGR_TO_COLOR : dict[str, str] = {
    "31": "red",
    "32": "green",
    "33": "yellow",
    "34": "blue",
    "35": "magenta",
    "91": "red",
    "92": "green",
    "93": "yellow",
    "94": "blue",
    "95": "magenta",
}

ACTORS : dict[str, str] = {
    "blue": "Attacker",
    "green": "Enclave",
    "yellow": "No actor",
    "magenta": "Interrupt",
    "red": "Reset",
}

RUN_SEPARATOR_RE = re.compile(r"\x1b\[1;33m.")
COLOR_SEPARATOR_RE = re.compile(r"\x1b\[([0-9;]*)m|([^\x1b]+)", re.DOTALL)

def run_alvie(
        alvie_path: Path, 
        executable_name : str,
        args: list[str],
        std_output : bool = False
    ) -> None:

    # execute if file .ml is modified
    # subprocess.run(["dune", "build"],
    #                 cwd=alvie_path,
    #                 check=True
    #                 )
    
    exe = f"{alvie_path}/_build/default/bin/{executable_name}.exe"
    print(f"\nRunning {exe} with arguments")
    for i in range(len(args)//2):
        print(f"\t{args[2*i]}: {args[2*i+1]}")
    print()

    if std_output:
        subprocess.run(
            [exe, *args], 
            cwd=alvie_path, 
            check=True
        )
    else:
        process = subprocess.run(
            [exe, *args],
            cwd=alvie_path,
            capture_output=True,
            text=True,
            check=True
        )
        raw_res = process.stdout
        print_alvie_output(raw_res)


def print_alvie_output(raw_res : str):
    symbols : dict = load_output_symbols()
    input_symbols, output_symbols = symbols["inputs"], symbols["outputs"]
    output_counts: Counter[str] = Counter()

    raw_hypotheses : list[str] = raw_res.splitlines()

    for i, raw_hypothesis in enumerate(raw_hypotheses):
        if raw_hypothesis:
            print(f"Hypothesis {i+1}\n\n")
            hypothesis = parse_hypothesis(
                raw_hypothesis=raw_hypothesis, 
                input_symbols=input_symbols,
                output_symbols=output_symbols,
                output_counts=output_counts,
            ) 
            print(hypothesis) 
            print("\n")

    print_recap(output_symbols, output_counts)


def print_recap(
        output_symbols: dict, 
        output_counts: Counter[str]
) -> None:
    """Print the total occurrences of each output symbol."""
    print(f"Recap\n")

    for symbol, data in output_symbols.items():
        print(f"\t{data['description']} {symbol}: {output_counts[symbol]}") 

    print()  


def parse_hypothesis(
        raw_hypothesis: str,
        input_symbols: dict,
        output_symbols: dict,
        output_counts: Counter[str],
) -> str:
    """Parse one hypothesis containing several runs."""
    parsed_runs = [
        parse_run(
            raw_run=raw_run,
            input_symbols=input_symbols,
            output_symbols=output_symbols,
            output_counts=output_counts,
        )
        for raw_run in RUN_SEPARATOR_RE.split(raw_hypothesis)
        if raw_run
    ]

    runs_text = "\n".join(
        f"Run {run_number}:\n{run}"
        for run_number, run in enumerate(parsed_runs, start=1)
    )

    return runs_text


def parse_run(
        raw_run: str,
        input_symbols: dict,
        output_symbols: dict,
        output_counts: Counter[str],
) -> str:
    """Parse one run containing several steps."""
    steps : list[str] = []
    input_step : list[str] = []
    output_step : list[str] = []    
    actor: str | None = None

    # iterate over color codes and symbols in the raw run
    for sgr_code, symbol in COLOR_SEPARATOR_RE.findall(raw_run):
        if sgr_code:
            color = SGR_TO_COLOR.get(sgr_code, None)
            if not color:
                continue
            
            actor = ACTORS[color]
        else:
            if "]" in symbol:
                # end of a step
                steps.append(format_step(input_step, output_step))
                input_step.clear()
                output_step.clear()
                actor = None

            elif "[" in symbol:
                continue
        
            else:
                input_symbol = input_symbols.get(symbol, None)
                if input_symbol:
                    input_step.append(format_symbol(actor, symbol, input_symbol['description']))
                else:
                    output_symbol = output_symbols.get(symbol, None)
                    if output_symbol:
                        output_step.append(format_symbol(actor, symbol, output_symbol['description']))
                        output_counts[symbol] += 1
    
    return "".join(steps)


def format_step(
        input_step: list[str], 
        output_step: list[str]
) -> str:
    """Format a step containing several input and output symbols."""
    inputs = " & ".join(input_step)
    outputs = " & ".join(output_step)
    return f"\t{inputs} -> {outputs}\n\n"


def format_symbol(
        actor: str | None,
        symbol: str,
        description: str
) -> str:
    """Format a parsed input or output symbol."""
    actor_name = actor or "Unknown actor"
    return f"{actor_name}: {description} ({symbol})"