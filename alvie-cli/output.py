import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from collections import Counter
import re

from utils import load_output_symbols
from output_models import ParsedHypothesis, ParsedRun, ParsedStep, ParsedSymbol

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[38;2;110;230;220m"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _style(text: str, *codes: str) -> str:
    if not _supports_color():
        return text
    return f"{''.join(codes)}{text}{RESET}"


def info(message: str) -> None:
    print(_style(message, CYAN))


def success(message: str) -> None:
    print(_style(message, GREEN, BOLD))


def warn(message: str) -> None:
    print(_style(message, YELLOW, BOLD))


def error(message: str) -> None:
    print(_style(message, RED, BOLD))


def hint(message: str) -> None:
    print(_style(message, DIM))


class Spinner:
    """Show a colored message with dots that appear and disappear while waiting."""

    def __init__(self, message: str, max_dots: int = 3, interval: float = 0.4):
        self.message = message
        self.max_dots = max_dots
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._animated = _supports_color()

    def start(self) -> "Spinner":
        if not self._animated:
            info(self.message)
            return self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        colored = _style(self.message, CYAN)
        step = 0
        while not self._stop.is_set():
            dots = "." * (step % (self.max_dots + 1))
            padding = " " * (self.max_dots - len(dots))
            sys.stdout.write(f"\r{colored}{dots}{padding}")
            sys.stdout.flush()
            step += 1
            self._stop.wait(self.interval)

    def stop(self) -> None:
        if not self._animated:
            return
        self._animated = False
        self._stop.set()
        if self._thread:
            self._thread.join()
        # Erase the animated line so the next output starts clean.
        sys.stdout.write("\r" + " " * (len(self.message) + self.max_dots) + "\r")
        sys.stdout.flush()

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

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


def color_from_sgr(sgr_code: str) -> str | None:
    """Return the semantic color from a plain or styled ANSI SGR code."""
    for code in reversed(sgr_code.split(";")):
        color = SGR_TO_COLOR.get(code)
        if color:
            return color

    return None

def run_alvie(
        alvie_path: Path, 
        executable_name : str,
        args: list[str],
        is_raw_output : bool = False,
        json_output_path: Path | None = None
    ) -> None:
    
    exe = f"{alvie_path}/_build/default/bin/{executable_name}"

    print()
    info(f"Running {_style(executable_name, CYAN, BOLD)}")
    hint(f"  {exe}\n")
    if args:
        info("Arguments:")
        for i in range(len(args)//2):
            print(f"\t{_style(args[2*i], CYAN)}: {args[2*i+1]}")
    else:
        hint("  (no arguments)")
    hint("\nPress Ctrl+C to stop the execution.")
    print()

    process: subprocess.Popen | None = None
    spinner: Spinner | None = None
    
    try:
        if is_raw_output:
            info("Streaming raw output")
            print()
            process = subprocess.Popen(
                [exe, *args],
                cwd=alvie_path,
                stderr=subprocess.PIPE,
                text=True
            )
            process.wait()            
            print("\n")
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, exe)
        else:
            process = subprocess.Popen(
                [exe, *args],
                cwd=alvie_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            symbols = load_output_symbols()
            input_symbols, output_symbols = symbols["inputs"], symbols["outputs"]
            output_counts: Counter[str] = Counter()
            parsed_hypotheses: list[ParsedHypothesis] = []

            raw_output = process.stdout
            if not raw_output:
                raise RuntimeError("No output from Alvie process.")

            spinner = Spinner("Waiting for Alvie to produce hypotheses").start()

            for i, line in enumerate(raw_output):
                if line.strip():
                    spinner.stop()
                    print(f"Hypothesis {i+1}\n")
                    hypothesis = parse_hypothesis(
                        raw_hypothesis=line.strip(),
                        input_symbols=input_symbols,
                        output_symbols=output_symbols,
                        output_counts=output_counts,
                    )
                    parsed_hypotheses.append(hypothesis)
                    print(format_hypothesis(hypothesis), flush=True)
                    spinner = Spinner("Waiting for the next hypothesis").start()

            spinner.stop()
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, exe)

            print_recap(output_symbols, output_counts)
            save_parsed_output(json_output_path, parsed_hypotheses, output_counts)

        success("Alvie finished successfully.\n")
    except KeyboardInterrupt:
        if spinner:
            spinner.stop()
        
        _terminate(process, force=True) # ctrl+c sends SIGKILL to the process        
            
        # if process and process.stderr:
        #     try:
        #         process.stderr.close()
        #     except:
        #         pass
            
        print()
        warn("Execution interrupted by user.\n")
    except subprocess.CalledProcessError as exc:
        if spinner:
            spinner.stop()
            
        error(f"Alvie exited with a non-zero status ({exc.returncode}).\n")

        # print legitimate error messages from Alvie's stderr
        if process and process.stderr:
            try:
                stderr_output = process.stderr.read()
                if stderr_output:
                    print(stderr_output)
            except:
                pass

def _terminate(process: subprocess.Popen | None, force: bool = False) -> None:
    """Stop a running Alvie process, escalating to a kill if it does not exit."""
    if process is None or process.poll() is not None:
        return
    
    if force:
        # ctr+c sends SIGKILL to the process
        process.kill()
    else:
        # graceful stutdown with SIGTERM, then escalate to SIGKILL if it does not exit
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            warn("Alvie did not stop in time, forcing termination.\n")
            process.kill()
            process.wait()


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
            print(format_hypothesis(hypothesis)) 
            print("\n")

    print_recap(output_symbols, output_counts)


def print_recap(
        output_symbols: dict, 
        output_counts: Counter[str]
) -> None:
    """Print the total occurrences of each output symbol."""
    print(f"Recap\n")

    for symbol, data in output_symbols.items():
        print(f"\t{data['name']} ({symbol}): {output_counts[symbol]}") 

    print()  


def save_parsed_output(
        output_path: Path | None,
        hypotheses: list[ParsedHypothesis],
        output_counts: Counter[str],
) -> None:
    """Save parsed output as JSON when an output path is provided."""
    if not output_path:
        return

    output_data = build_output_json(hypotheses, output_counts)

    try:
        write_output_json(output_data, output_path)
        info(f"Parsed output saved to {_style(str(output_path), CYAN, BOLD)}\n")
    except OSError as exc:
        warn(f"Could not save parsed output JSON: {exc}\n")


def build_output_json(
        hypotheses: list[ParsedHypothesis],
        output_counts: Counter[str],
) -> dict:
    """Build the JSON-serializable parsed output document."""
    return {
        "hypotheses": [hypothesis.to_dict() for hypothesis in hypotheses],
        "recap": {
            symbol: count
            for symbol, count in output_counts.items()
            if count > 0
        },
    }


def write_output_json(output_data: dict, output_path: Path) -> None:
    """Write parsed output JSON, creating parent directories if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_hypothesis(
        raw_hypothesis: str,
        input_symbols: dict,
        output_symbols: dict,
        output_counts: Counter[str],
) -> ParsedHypothesis:
    """Parse one hypothesis containing several runs."""
    runs: list[ParsedRun] = []

    raw_runs = [raw_run for raw_run in RUN_SEPARATOR_RE.split(raw_hypothesis) if raw_run]
    for raw_run in raw_runs:
        runs.append(parse_run(
            raw_run=raw_run,
            input_symbols=input_symbols,
            output_symbols=output_symbols,
            output_counts=output_counts,
        ))

    return ParsedHypothesis(runs=runs)


def parse_run(
        raw_run: str,
        input_symbols: dict,
        output_symbols: dict,
        output_counts: Counter[str],
) -> ParsedRun:
    """Parse one run containing several steps."""
    steps : list[ParsedStep] = []
    input_step : list[ParsedSymbol] = []
    output_step : list[ParsedSymbol] = []    
    actor: str | None = None
    color: str | None = None
    is_output = False

    # iterate over color codes and symbols in the raw run
    for sgr_code, text in COLOR_SEPARATOR_RE.findall(raw_run):
        if sgr_code:
            color = color_from_sgr(sgr_code)
            if not color:
                continue
            
            actor = ACTORS[color]
        else:
            for token in tokenize_step_text(text, input_symbols, output_symbols):
                if token == "[":
                    is_output = False
                    continue

                if token == "]":
                    steps.append(ParsedStep(inputs=input_step.copy(), outputs=output_step.copy()))
                    input_step.clear()
                    output_step.clear()
                    actor = None
                    color = None
                    is_output = False
                    continue

                if is_output:
                    output_symbol = output_symbols.get(token, None)
                    if output_symbol:
                        output_step.append(parse_symbol(actor, color, token, output_symbol))
                        output_counts[token] += 1
                else:
                    input_symbol = input_symbols.get(token, None)
                    if input_symbol:
                        input_step.append(parse_symbol(actor, color, token, input_symbol))
                        is_output = True
    
    return ParsedRun(steps=steps)


def tokenize_step_text(
        text: str,
        input_symbols: dict,
        output_symbols: dict,
) -> list[str]:
    """Split bracketed ALVIE text into delimiters and known symbols."""
    symbols = sorted(
        [*input_symbols.keys(), *output_symbols.keys()],
        key=len,
        reverse=True,
    )
    tokens: list[str] = []
    index = 0

    while index < len(text):
        char = text[index]

        if char.isspace():
            index += 1
            continue

        if char in "[]":
            tokens.append(char)
            index += 1
            continue

        match = next((symbol for symbol in symbols if text.startswith(symbol, index)), None)
        if match:
            tokens.append(match)
            index += len(match)
            continue

        index += 1

    return tokens


def parse_symbol(
        actor: str | None,
        color: str | None,
        symbol: str,
        symbol_data: dict,
) -> ParsedSymbol:
    """Build a parsed symbol from the config entry and active ANSI color."""
    return ParsedSymbol(
        symbol=symbol,
        name=symbol_data["name"],
        description=symbol_data["description"],
        actor=actor or "Unknown actor",
        color=color,
    )


def format_hypothesis(hypothesis: ParsedHypothesis) -> str:
    """Format a parsed hypothesis for terminal output."""
    return "".join(
        format_run(run, run_number)
        for run_number, run in enumerate(hypothesis.runs, start=1)
    )


def format_run(run: ParsedRun, number: int) -> str:
    """Format a parsed run for terminal output."""
    steps = "".join(format_step(step) for step in run.steps)
    return f"Run {number}:\n{steps}"


def format_step(
        step: ParsedStep
) -> str:
    """Format a step containing several input and output symbols."""
    inputs = " & ".join(format_symbol(symbol) for symbol in step.inputs)
    outputs = " & ".join(format_symbol(symbol) for symbol in step.outputs)
    return f"\t{inputs} -> {outputs}\n\n"


def format_symbol(
        symbol: ParsedSymbol
) -> str:
    """Format a parsed input or output symbol."""
    return f"{symbol.actor}: {symbol.name} ({symbol.symbol})"
