from datetime import datetime
from io import TextIOWrapper
import os
import sys
import time
import json
import threading
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter
import re
import shutil
from typing import IO

from utils import load_output_symbols
from flows import ConfigArg, is_debug_enabled

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

DEBUG_PARSED_OUTPUT_ERROR = (
    "Cannot use --debug together with --parsed-output."
)
DEBUG_REQUIRES_RAW_OUTPUT_ERROR = (
    "Alvie's --debug output cannot be parsed reliably. Use --raw-output (-r)."
)

LOGO_LINES = [
    " █████╗  ██╗     ██╗   ██╗ ██╗ ███████╗       ██████╗ ██╗     ██╗",
    "██╔══██╗ ██║     ██║   ██║ ██║ ██╔════╝      ██╔════╝ ██║     ██║",
    "███████║ ██║     ██║   ██║ ██║ █████╗        ██║      ██║     ██║",
    "██╔══██║ ██║     ╚██╗ ██╔╝ ██║ ██╔══╝        ██║      ██║     ██║",
    "██║  ██║ ███████╗ ╚████╔╝  ██║ ███████╗      ╚██████╗ ███████╗██║",
    "╚═╝  ╚═╝ ╚══════╝  ╚═══╝   ╚═╝ ╚══════╝       ╚═════╝ ╚══════╝╚═╝",
]

# Gradient endpoints (blue -> cyan).
GRADIENT_START = (80, 150, 255)
GRADIENT_END = (110, 230, 220)

TAGLINE = "Interface for the Alvie analysis tool"
TIP = "Pick an action below  ·  Ctrl+C to exit"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _color_from_sgr(sgr_code: str) -> str | None:
    """Return the semantic color from a plain or styled ANSI SGR code."""
    for code in reversed(sgr_code.split(";")):
        color = SGR_TO_COLOR.get(code)
        if color:
            return color

    return None


def _truecolor(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _gradient_line(text: str, ratio: float) -> str:
    sr, sg, sb = GRADIENT_START
    er, eg, eb = GRADIENT_END
    r = round(sr + (er - sr) * ratio)
    g = round(sg + (eg - sg) * ratio)
    b = round(sb + (eb - sb) * ratio)
    return f"{BOLD}{_truecolor(r, g, b)}{text}{RESET}"


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


class ParallelDashboard:
    """Live terminal dashboard for parallel ALVIE executions.

    Renders one status line per execution and rewrites the whole block in place
    (ANSI cursor moves) so each line flips queued -> running -> done/failed as
    soon as its thread changes state, with an animated spinner and a live
    elapsed-time counter. Degrades to plain one-shot prints when stdout is not a
    color-capable TTY."""

    QUEUED, RUNNING, DONE, FAILED = "queued", "running", "done", "failed"

    _BADGES: dict[str, tuple[str, str, str]] = {
        QUEUED: (DIM, "·", "QUEUED"),
        RUNNING: (CYAN, "", "RUNNING"),  # icon replaced by spinner frame
        DONE: (GREEN, "✓", "DONE"),
        FAILED: (RED, "✗", "FAILED"),
    }
    _SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, labels: list[str], interval: float = 0.1):
        self.labels = labels
        self.interval = interval
        self._states = [self.QUEUED] * len(labels)
        self._starts: list[float | None] = [None] * len(labels)
        self._ends: list[float | None] = [None] * len(labels)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._animated = _supports_color()
        self._frame = 0
        self._rendered_lines = 0

    def start(self) -> "ParallelDashboard":
        if not self._animated:
            info(f"Running {len(self.labels)} executions in parallel "
                 f"({self._max_label_state()})")
            return self
        sys.stdout.write("\033[?25l")  # hide cursor
        self._render()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def set_running(self, index: int) -> None:
        self._transition(index, self.RUNNING)

    def set_done(self, index: int) -> None:
        self._transition(index, self.DONE)

    def set_failed(self, index: int) -> None:
        self._transition(index, self.FAILED)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._animated:
            self._render()
            sys.stdout.write("\033[?25h")  # show cursor
            sys.stdout.flush()

    def __enter__(self) -> "ParallelDashboard":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    def _transition(self, index: int, state: str) -> None:
        with self._lock:
            now = time.monotonic()
            if state == self.RUNNING:
                self._starts[index] = now
            elif state in (self.DONE, self.FAILED):
                self._ends[index] = now
            self._states[index] = state
        if not self._animated:
            color, icon, text = self._BADGES[state]
            line = f"  {_style(f'{icon} {text}', color, BOLD)}  {self.labels[index]}"
            if state in (self.DONE, self.FAILED):
                print(f"{line}  {_style(f'{self._elapsed(index):.1f}s', DIM)}")
            return
        self._render()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._frame += 1
            self._render()
            self._stop.wait(self.interval)

    def _elapsed(self, index: int) -> float:
        start = self._starts[index]
        if start is None:
            return 0.0
        end = self._ends[index] if self._ends[index] is not None else time.monotonic()
        if end is None:
            return 0.0
        return end - start

    def _max_label_state(self) -> str:
        done = sum(s in (self.DONE, self.FAILED) for s in self._states)
        return f"{done}/{len(self._states)} finished"

    def _format_line(self, index: int) -> str:
        state = self._states[index]
        color, icon, text = self._BADGES[state]
        if state == self.RUNNING:
            icon = self._SPINNER_FRAMES[self._frame % len(self._SPINNER_FRAMES)]
        badge = _style(f"{icon} {text:<7}", color, BOLD)
        elapsed = ""
        if self._starts[index] is not None:
            elapsed = _style(f"{self._elapsed(index):6.1f}s", DIM)
        return f"  {badge}  {self.labels[index]}  {elapsed}"

    def _progress_bar(self, done: int, total: int, width: int = 24) -> str:
        filled = round(width * done / total) if total else 0
        return _style("█" * filled, GREEN) + _style("░" * (width - filled), DIM)

    def _render(self) -> None:
        if not self._animated:
            return
        with self._lock:
            done = sum(s in (self.DONE, self.FAILED) for s in self._states)
            failed = sum(s == self.FAILED for s in self._states)
            total = len(self._states)
            header = _style("Parallel execution", CYAN, BOLD)
            counter = _style(f"{done}/{total}", CYAN, BOLD)
            if failed:
                counter += " " + _style(f"({failed} failed)", RED, BOLD)
            lines = [f"{header}  {self._progress_bar(done, total)}  {counter}"]
            lines += [self._format_line(i) for i in range(total)]

            buffer = []
            if self._rendered_lines:
                buffer.append(f"\033[{self._rendered_lines}F")  # cursor up to block top
            buffer += [f"\033[2K{line}\n" for line in lines]
            sys.stdout.write("".join(buffer))
            sys.stdout.flush()
            self._rendered_lines = len(lines)


@dataclass 
class SymbolParser:
    input_symbols: dict
    output_symbols: dict


@dataclass
class ParsedOutput:
    parsed_hypotheses: list["ParsedHypothesis"] = field(default_factory=list)
    output_counts: Counter[str] = field(default_factory=Counter)

    hypotheses_count: int = field(init=False, default=0)
    runs_count: int = field(init=False, default=0)
    steps_count: int = field(init=False, default=0)

    def format_recap(
        self,
        parser: SymbolParser
    ) -> str:
        """Format the total occurrences of number of hypotheses, runs, steps and output symbol."""
        
        lines = [
            "Recap\n",
            f"\tHypotheses: {self.hypotheses_count}",
            f"\tRuns: {self.runs_count}",
            f"\tSteps: {self.steps_count}",
            "\n\tOutputs:",
        ]
        
        # show only output symbols with non-zero occurrences
        for symbol, data in parser.output_symbols.items():
            if self.output_counts[symbol] > 0:
                lines.append(f"\t- {data['name']} ({symbol}): {self.output_counts[symbol]}")
        return "\n".join(lines) + "\n"


@dataclass 
class ParsedSymbol:
    symbol: str
    name: str
    description: str
    actor: str
    color: str | None

    # JSON parser: attacker, enclave share some input symbols, so we distinguish them by actor
    def to_input_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "actor": self.actor,
        }

    def format(self) -> str:
        """Format a parsed input or output symbol."""
        return f"{self.actor}: {self.name} ({self.symbol})"
    
    @classmethod
    def parse(
        cls,
        actor: str | None,
        color: str | None,
        symbol: str,
        symbol_data: dict,
    ) -> "ParsedSymbol":
        """Build a parsed symbol from the config entry and active ANSI color."""
        return ParsedSymbol(
            symbol=symbol,
            name=symbol_data["name"],
            description=symbol_data["description"],
            actor=actor or "Unknown actor",
            color=color,
        )


@dataclass
class ParsedStep:
    # create a new list for each instance
    # [] would create a single shared list by all instances
    inputs: list[ParsedSymbol] = field(default_factory=list)
    outputs: list[ParsedSymbol] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "inputs": [symbol.to_input_dict() for symbol in self.inputs],
            "outputs": [symbol.symbol for symbol in self.outputs],
        }
    
    def format(self) -> str:
        """Format a step containing several input and output symbols."""
        inputs = " & ".join(symbol.format() for symbol in self.inputs)
        outputs = " & ".join(symbol.format() for symbol in self.outputs)
        return f"\t{inputs} -> {outputs}\n\n"
    
    @classmethod
    def tokenize(
        cls,
        raw: str,
        parser: SymbolParser
    ) -> list[str]:
        """Split bracketed ALVIE text into delimiters and known symbols."""
        symbols = sorted(
            [*parser.input_symbols.keys(), *parser.output_symbols.keys()],
            key=len,
            reverse=True,
        )
        tokens: list[str] = []
        index = 0

        while index < len(raw):
            char = raw[index]

            if char.isspace():
                index += 1
                continue

            if char in "[]":
                tokens.append(char)
                index += 1
                continue

            match = next((symbol for symbol in symbols if raw.startswith(symbol, index)), None)
            if match:
                tokens.append(match)
                index += len(match)
                continue

            index += 1

        return tokens

@dataclass
class ParsedRun:
    steps: list[ParsedStep] = field(default_factory=list)

    def to_dict(self) -> list[dict]:
        return [step.to_dict() for step in self.steps]
    
    def format(self, number: int) -> str:
        """Format a parsed run for terminal output."""
        steps = "".join(step.format() for step in self.steps)
        return f"Run {number}:\n{steps}"
    
    @classmethod
    def parse(
        cls, 
        raw_run: str, 
        parser: SymbolParser,
        output: ParsedOutput
    ) -> "ParsedRun":
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
                color = _color_from_sgr(sgr_code)
                if not color:
                    continue
                
                actor = ACTORS[color]
            else:
                for token in ParsedStep.tokenize(
                    raw=text, 
                    parser=parser
                ):
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
                        output_symbol = parser.output_symbols.get(token, None)
                        if output_symbol:
                            output_step.append(
                                ParsedSymbol.parse(
                                    actor=actor, 
                                    color=color, 
                                    symbol=token, 
                                    symbol_data=output_symbol
                                ))
                            output.output_counts[token] += 1
                    else:
                        input_symbol = parser.input_symbols.get(token, None)
                        if input_symbol:
                            input_step.append(
                                ParsedSymbol.parse(
                                    actor=actor, 
                                    color=color, 
                                    symbol=token, 
                                    symbol_data=input_symbol
                                ))
                            is_output = True
    
        output.steps_count += len(steps)
        return ParsedRun(steps=steps)


@dataclass
class ParsedHypothesis:
    runs: list[ParsedRun] = field(default_factory=list)

    def to_dict(self) -> list[list[dict]]:
        return [run.to_dict() for run in self.runs]
    
    def format(self) -> str:
        """Format a parsed hypothesis for terminal output."""
        return "".join(
            run.format(run_number)
            for run_number, run in enumerate(self.runs, start=1)
        )
    
    @classmethod
    def parse(
        cls, 
        raw : str, 
        parser : SymbolParser,
        output: ParsedOutput
    ) -> "ParsedHypothesis":
        """Parse one hypothesis containing several runs."""
        runs: list[ParsedRun] = []

        raw_runs = [raw_run for raw_run in RUN_SEPARATOR_RE.split(raw) if raw_run]
        for raw_run in raw_runs:
            runs.append(ParsedRun.parse(
                raw_run=raw_run,
                parser=parser,
                output=output
            ))
        
        output.runs_count += len(runs)
        return ParsedHypothesis(runs=runs)


@dataclass
class AlvieExecution:
    """A single ALVIE execution with its arguments and output settings."""

    alvie_path: Path
    executable: str
    args: list[ConfigArg] = field(default_factory=list)
    is_raw_output: bool = field(default=False)
    output_path: Path | None = field(default=None)
    parsed_output_path: Path | None = field(default=None)
    parallel: bool = field(default=False)

    _process: subprocess.Popen | None = field(default=None, init=False, repr=False)
    _spinner: Spinner | None = field(default=None, init=False, repr=False)
    _output_file: TextIOWrapper | None = field(default=None, init=False, repr=False)

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
        """Run the ALVIE execution with the specified output mode"""
        try:
            if is_debug_enabled(self.args) and self.parsed_output_path is not None:
                raise ValueError(DEBUG_PARSED_OUTPUT_ERROR)

            self._open_output_file()
            self._start_time = datetime.now()
            self._write_header()    

            if self.is_raw_output:
                self._run_raw()
            else:
                self._run_parsed()

        except KeyboardInterrupt:
            self._stop_spinner()
            self._terminate(force=True)  # ctrl+c sends SIGKILL to the process
            print()
            warn("Execution interrupted by user.\n")

        except subprocess.CalledProcessError as exc:
            self._stop_spinner()
            error(f"Alvie exited with a non-zero status ({exc.returncode}).\n")

        finally:
            self._close_output_file()


    def run_seq(self) -> None:
        """Run ALVIE execution with sequential output to the terminal"""
        self._print_header()
        self._process = None

        self._spinner = Spinner("Executing ALVIE").start()
        self.run()
        success("Alvie finished successfully.\n")


    def _run_raw(self) -> None:
        """Run the ALVIE execution and stream its raw output to the terminal or file."""
        try:
            self._process, stdout = self._get_alvie_process()
            received_output = False
            for line in stdout:
                if not received_output:
                    self._stop_spinner()
                    received_output = True
                self._write(line, end="", flush=True)

            self._write("\n\n")
            self._process.wait()
            self._end_time = datetime.now()

            if self._process.returncode != 0:
                raise subprocess.CalledProcessError(self._process.returncode, self.exe)
        finally:
            self._stop_spinner()


    def _run_parsed(self) -> None:
        """Run the ALVIE execution and parse its output."""
        self._process, stdout = self._get_alvie_process()

        symbols = load_output_symbols()
        input_symbols, output_symbols = symbols["inputs"], symbols["outputs"]
        parser = SymbolParser(
            input_symbols=input_symbols,
            output_symbols=output_symbols
        )

        output = ParsedOutput()

        for i, line in enumerate(stdout):
            if line.strip():
                self._stop_spinner()
                hypothesis = ParsedHypothesis.parse(
                    raw=line.strip(),
                    parser=parser,
                    output=output
                )
                output.parsed_hypotheses.append(hypothesis)
                # non-raw output is written only if an output file is specified, otherwise only the recap is printed to the terminal
                if self._output_file:
                    formatted_hypothesis = hypothesis.format()
                    self._write(f"Hypothesis {i+1}\n", formatted_hypothesis, flush=True)
                if not self.parallel:
                    self._spinner = Spinner(f"Waiting for the next hypothesis {i+2}").start()

        self._stop_spinner()
        self._process.wait()
        self._end_time = datetime.now()

        if self._process.returncode != 0:
            raise subprocess.CalledProcessError(self._process.returncode, self.exe)

        output.hypotheses_count = len(output.parsed_hypotheses)
        if not self.parallel:
            self._write(output.format_recap(parser=parser), flush=True)
        self._save_parsed_output(output=output)


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


    def _write_header(self) -> None:
        """Write a header with execution information to the output file."""
        if not self._output_file:
            return

        started = (
            self._start_time.isoformat(sep=" ", timespec="seconds")
            if self._start_time else "unknown"
        )

        lines = [
            "=" * 60,
            "Start of ALVIE execution",
            f"Executable : {self.executable}",
            f"Path       : {self.exe}",
            f"Output mode       : {'raw' if self.is_raw_output else 'parsed'}",
            f"Started    : {started}",
            "Arguments  :",
        ]
        if self.args:
            for arg in self.args:
                if arg.value is not None:
                    lines.append(f"  {arg.flag}: {arg.value}")
                else:
                    lines.append(f"  {arg.flag}")
        else:
            lines.append("  (no arguments)")
        lines.append("=" * 60)

        self._write("\n".join(lines) + "\n")


    def _write_footer(self) -> None:
        """Write a footer with execution timing to the output file."""
        if not self._output_file:
            return

        ended = (
            self._end_time.isoformat(sep=" ", timespec="seconds")
            if self._end_time else "unknown"
        )

        lines = [
            "=" * 60,
            "End of ALVIE execution",
            f"Finished   : {ended}",
        ]
        if self._start_time and self._end_time:
            lines.append(f"Duration   : {self._end_time - self._start_time}")
        lines.append("=" * 60)

        self._write("\n" + "\n".join(lines) + "\n")


    def _write(
            self, 
            text: str = "", 
            end: str = "\n", 
            flush: bool = False,
        ) -> None:
        """Write produced output to the output file when set, otherwise to the terminal."""

        if self._output_file:
            self._output_file.write(f"{text}{end}")
        else:
            print(text, end=end, flush=flush)


    def _save_parsed_output(
        self,
        output: ParsedOutput,
    ) -> None:
        """Save parsed output as JSON when an output path is provided."""
        if not self.parsed_output_path:
            return

        output_data = self._build_output_json(output=output)

        try:
            self.parsed_output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.parsed_output_path.open("w", encoding="utf-8") as file:
                json.dump(output_data, file, ensure_ascii=False, indent=2)
            if not self.parallel:
                print()
                info(f"Parsed output saved to {_style(str(self.parsed_output_path), CYAN, BOLD)}\n")
        except OSError as exc:
            warn(f"Could not save parsed output JSON: {exc}\n")


    def _open_output_file(self) -> None:
        """Open the output file for writing when an output path is provided."""
        self._output_file = None
        if not self.output_path:
            return
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._output_file = self.output_path.open("w", encoding="utf-8")
        except OSError as exc:
            warn(f"Could not open output file, writing to terminal instead: {exc}\n")
            self._output_file = None


    def _close_output_file(self) -> None:
        """Close the output file"""
        if not self._output_file:
            return
        self._write_footer()
        self._output_file.close()
        self._output_file = None
        if not self.parallel:
            info(f"Output saved to {_style(str(self.output_path), CYAN, BOLD)}\n")


    def _build_output_json(
        self,
        output: ParsedOutput,
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
                for symbol, count in output.output_counts.items()
                if count > 0
            } | {
                "hypotheses": output.hypotheses_count,
                "runs": output.runs_count,
                "steps": output.steps_count
            },
            "hypotheses": [hypothesis.to_dict() for hypothesis in output.parsed_hypotheses],
        }


    def _get_alvie_process(self) -> tuple[subprocess.Popen, IO[str]]:
        """Return the ALVIE process and its stdout stream"""
        process = subprocess.Popen(
            self.command,
            cwd=self.alvie_path,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True
        )

        if not process:
            raise RuntimeError("Alvie process could not be started.")
        
        if not process.stdout:
            raise RuntimeError("No output from Alvie process.")
        
        return process, process.stdout


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


def print_banner() -> None:
    """Print the Alvie CLI welcome banner."""
    color = _supports_color()
    width = max(len(line) for line in LOGO_LINES)
    pad = "  "

    print()
    for i, line in enumerate(LOGO_LINES):
        ratio = i / (len(LOGO_LINES) - 1)
        rendered = _gradient_line(line, ratio) if color else line
        print(f"{pad}{rendered}")
    print()

    # Rounded info box, sized to the widest content line (logo or text).
    box_texts = ["✻ Welcome to Alvie CLI", "", TAGLINE, TIP]
    inner = max(width, *(len(t) for t in box_texts))
    top = f"╭{'─' * (inner + 2)}╮"
    bottom = f"╰{'─' * (inner + 2)}╯"

    def box_line(text: str, *, accent: bool = False) -> str:
        body = f"│ {text.ljust(inner)} │"
        if not color:
            return f"{pad}{body}"
        style = BOLD if accent else DIM
        return f"{pad}{DIM}│{RESET} {style}{text.ljust(inner)}{RESET} {DIM}│{RESET}"

    edge = f"{pad}{DIM}{top}{RESET}" if color else f"{pad}{top}"
    edge_b = f"{pad}{DIM}{bottom}{RESET}" if color else f"{pad}{bottom}"

    print(edge)
    print(box_line("✻ Welcome to Alvie CLI", accent=True))
    print(box_line(""))
    print(box_line(TAGLINE))
    print(box_line(TIP))
    print(edge_b)
    print()