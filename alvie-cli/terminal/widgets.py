import threading
import sys
import time

from .style import (
    style, 
    CYAN, 
    GREEN, 
    RED, 
    DIM, 
    BOLD,
    supports_color,
    info,
)

class Spinner:
    """Show a colored message with dots that appear and disappear while waiting."""

    def __init__(self, message: str, max_dots: int = 3, interval: float = 0.4):
        self.message = message
        self.max_dots = max_dots
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._animated = supports_color()

    def start(self) -> "Spinner":
        if not self._animated:
            info(self.message)
            return self
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        colored = style(self.message, CYAN)
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
        self._animated = supports_color()
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
            line = f"  {style(f'{icon} {text}', color, BOLD)}  {self.labels[index]}"
            if state in (self.DONE, self.FAILED):
                print(f"{line}  {style(f'{self._elapsed(index):.1f}s', DIM)}")
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
        badge = style(f"{icon} {text:<7}", color, BOLD)
        elapsed = ""
        if self._starts[index] is not None:
            elapsed = style(f"{self._elapsed(index):6.1f}s", DIM)
        return f"  {badge}  {self.labels[index]}  {elapsed}"

    def _progress_bar(self, done: int, total: int, width: int = 24) -> str:
        filled = round(width * done / total) if total else 0
        return style("█" * filled, GREEN) + style("░" * (width - filled), DIM)

    def _render(self) -> None:
        if not self._animated:
            return
        with self._lock:
            done = sum(s in (self.DONE, self.FAILED) for s in self._states)
            failed = sum(s == self.FAILED for s in self._states)
            total = len(self._states)
            header = style("Parallel execution", CYAN, BOLD)
            counter = style(f"{done}/{total}", CYAN, BOLD)
            if failed:
                counter += " " + style(f"({failed} failed)", RED, BOLD)
            lines = [f"{header}  {self._progress_bar(done, total)}  {counter}"]
            lines += [self._format_line(i) for i in range(total)]

            buffer = []
            if self._rendered_lines:
                buffer.append(f"\033[{self._rendered_lines}F")  # cursor up to block top
            buffer += [f"\033[2K{line}\n" for line in lines]
            sys.stdout.write("".join(buffer))
            sys.stdout.flush()
            self._rendered_lines = len(lines)