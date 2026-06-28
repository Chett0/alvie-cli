from datetime import datetime
import os
import sys
import json
import threading
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter
import re

from utils import load_output_symbols
from output_models import ParsedHypothesis, ParsedRun, ParsedStep, ParsedSymbol
from flows import ConfigArg

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[38;2;110;230;220m"

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


@dataclass
class AlvieExecution:
    """A single ALVIE execution with its arguments and output settings."""

    alvie_path: Path
    executable: str
    args: list[ConfigArg] = field(default_factory=list)
    is_raw_output: bool = False
    json_output_path: Path | None = None

    _process: subprocess.Popen | None = field(default=None, init=False, repr=False)
    _spinner: "Spinner | None" = field(default=None, init=False, repr=False)

    _start_time : datetime | None = field(default=None, init=False, repr=False)
    _end_time : datetime | None = field(default=None, init=False, repr=False)

    @property
    def exe(self) -> str:
        """Absolute path to the ALVIE executable to invoke."""
        return f"{self.alvie_path}/_build/default/bin/{self.executable}"

    @property
    def args_string(self) -> list[str]:
        """Arguments flattened into CLI tokens (``["--flag", "value", ...]``)."""
        tokens: list[str] = []
        for arg in self.args:
            tokens.append(arg.flag)
            if arg.value is not None:
                tokens.append(arg.value)
        return tokens

    @property
    def command(self) -> list[str]:
        """Full command line passed to the subprocess."""
        return [self.exe, *self.args_string]

    def run(self) -> None:
        """Start the ALVIE process"""
        self._print_header()

        self._process = None
        self._spinner = None

        try:
            self._start_time = datetime.now()

            if self.is_raw_output:
                self._run_raw()
            else:
                self._run_parsed()
            success("Alvie finished successfully.\n")
        
        except KeyboardInterrupt:
            self._stop_spinner()
            self._terminate(force=True)  # ctrl+c sends SIGKILL to the process
            print()
            warn("Execution interrupted by user.\n")

        except subprocess.CalledProcessError as exc:
            self._stop_spinner()
            error(f"Alvie exited with a non-zero status ({exc.returncode}).\n")
            self._print_stderr()  # print legitimate error messages from Alvie's stderr

    def _print_header(self) -> None:
        print()
        info(f"Running {_style(self.executable, CYAN, BOLD)}")
        hint(f"  {self.exe}\n")
        if self.args:
            info("Arguments:")
            for arg in self.args:
                if arg.value:
                    print(f"\t{_style(arg.flag, CYAN)}: {arg.value}")
                else:
                    print(f"\t{_style(arg.flag, CYAN)}")
        else:
            hint("  (no arguments)")
        hint("\nPress Ctrl+C to stop the execution.")
        print()

    def _run_raw(self) -> None:
        self._spinner = Spinner("Executing ALVIE").start()
        self._process = subprocess.Popen(
            self.command,
            cwd=self.alvie_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        raw_output = self._process.stdout
        if not raw_output:
            raise RuntimeError("No output from Alvie process.")

        stdout_output = raw_output.read()
        self._process.wait()
        self._end_time = datetime.now()

        self._stop_spinner()
        print()
        if stdout_output:
            print(stdout_output)
        print("\n")

        if self._process.returncode != 0:
            raise subprocess.CalledProcessError(self._process.returncode, self.exe)

    def _run_parsed(self) -> None:
        self._process = subprocess.Popen(
            self.command,
            cwd=self.alvie_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        symbols = load_output_symbols()
        input_symbols, output_symbols = symbols["inputs"], symbols["outputs"]
        output_counts: Counter[str] = Counter()
        parsed_hypotheses: list[ParsedHypothesis] = []

        raw_output = self._process.stdout
        if not raw_output:
            raise RuntimeError("No output from Alvie process.")

        self._spinner = Spinner("Waiting for Alvie to produce hypotheses").start()

        for i, line in enumerate(raw_output):
            if line.strip():
                self._stop_spinner()
                print(f"Hypothesis {i+1}\n")
                hypothesis = parse_hypothesis(
                    raw_hypothesis=line.strip(),
                    input_symbols=input_symbols,
                    output_symbols=output_symbols,
                    output_counts=output_counts,
                )
                parsed_hypotheses.append(hypothesis)
                print(format_hypothesis(hypothesis), flush=True)
                self._spinner = Spinner("Waiting for the next hypothesis").start()

        self._stop_spinner()
        self._process.wait()
        self._end_time = datetime.now()

        if self._process.returncode != 0:
            raise subprocess.CalledProcessError(self._process.returncode, self.exe)

        print_recap(output_symbols, output_counts)
        self._save_parsed_output(parsed_hypotheses, output_counts)

    def _stop_spinner(self) -> None:
        if self._spinner:
            self._spinner.stop()
            self._spinner = None

    def _terminate(self, force: bool = False) -> None:
        """Stop the running Alvie process, escalating to a kill if it does not exit."""
        process = self._process
        if process is None or process.poll() is not None:
            return

        if force:
            # ctrl+c sends SIGKILL to the process
            process.kill()
        else:
            # graceful shutdown with SIGTERM, then escalate to SIGKILL if it does not exit
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                warn("Alvie did not stop in time, forcing termination.\n")
                process.kill()
                process.wait()

    def _print_stderr(self) -> None:
        process = self._process
        if process and process.stderr:
            try:
                stderr_output = process.stderr.read()
                if stderr_output:
                    print(stderr_output)
            except OSError:
                pass

    def _save_parsed_output(
        self,
        hypotheses: list[ParsedHypothesis],
        output_counts: Counter[str],
    ) -> None:
        """Save parsed output as JSON when an output path is provided."""
        if not self.json_output_path:
            return

        output_data = self._build_output_json(hypotheses, output_counts)

        try:
            self.json_output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.json_output_path.open("w", encoding="utf-8") as file:
                json.dump(output_data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            info(f"Parsed output saved to {_style(str(self.json_output_path), CYAN, BOLD)}\n")
        except OSError as exc:
            warn(f"Could not save parsed output JSON: {exc}\n")

    def _build_output_json(
        self,
        hypotheses: list[ParsedHypothesis],
        output_counts: Counter[str],
    ) -> dict:
        """Build the JSON-serializable parsed output document."""
        return {
            "executable": self.executable,
            "args": [
                {"flag": arg.flag, "value": arg.value}
                if arg.value is not None
                else {"flag": arg.flag}
                for arg in self.args
            ],
            "start": self._start_time.isoformat() if self._start_time else None,
            "end": self._end_time.isoformat() if self._end_time else None,
            "recap": {
                symbol: count
                for symbol, count in output_counts.items()
                if count > 0
            },
            "hypotheses": [hypothesis.to_dict() for hypothesis in hypotheses],
        }



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
