from typing import Iterator
import os
import sys
import threading
import subprocess
from pathlib import Path
from collections import Counter
import re

from utils import load_output_symbols

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

def run_alvie(
        alvie_path: Path, 
        executable_name : str,
        args: list[str],
        is_raw_output : bool = False
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

            raw_output = process.stdout
            if not raw_output:
                raise RuntimeError("No output from Alvie process.")

            spinner = Spinner("Waiting for Alvie to produce hypotheses").start()

            for i, line in enumerate(raw_output):
                if line.strip():
                    spinner.stop()
                    print(f"Hypothesis {i+1}\n")
                    for run in parse_hypothesis(
                        raw_hypothesis=line.strip(),
                        input_symbols=input_symbols,
                        output_symbols=output_symbols,
                        output_counts=output_counts,
                    ):
                        print(run, flush=True)
                    spinner = Spinner("Waiting for the next hypothesis").start()

            spinner.stop()
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, exe)

            print_recap(output_symbols, output_counts)

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
) -> Iterator[str]:
    """Parse one hypothesis containing several runs."""

    for run_number, raw_run in enumerate(RUN_SEPARATOR_RE.split(raw_hypothesis), start=1):
        if raw_run:
            run = parse_run(
                raw_run=raw_run,
                input_symbols=input_symbols,
                output_symbols=output_symbols,
                output_counts=output_counts,
            )
            yield f"Run {run_number}:\n{run}"


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