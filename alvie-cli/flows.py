from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generic, TypeVar
from pydantic import BaseModel
from pathlib import Path
import sys

ESC = "\033["

ESC_INSTRUCTION = "ESC to go back"
HELP_INSTRUCTION = "F1 for help"
SHOW_INSTRUCTION = "F2 to show"

def create_prompt(prompt_cls, allow_back: bool = True, **kwargs):
    # TODO: add help and show instructions
    if allow_back and "long_instruction" not in kwargs:
        kwargs["long_instruction"] = ESC_INSTRUCTION

    prompt = prompt_cls(**kwargs)

    if allow_back:
        register_back(prompt)

    return prompt


def register_back(prompt) -> None:
    @prompt.register_kb("escape")
    def _register_back(event):
        event.app.exit(result=StepResult.BACK)

def register_help(prompt) -> None:
    @prompt.register_kb("f1")
    def _handle_f1(event):
        event.app.exit(result=StepResult.HELP)

def register_f2(prompt) -> None:
    @prompt.register_kb("f2")
    def _handle_show(event):
        event.app.exit(result=StepResult.SHOW)


class StepResult(Enum):
    NEXT = "next"
    BACK = "back"
    SHOW = "show"
    HELP = "help"
    STAY = "stay"

@dataclass(frozen=True)
class StepOutput:
    step_result: StepResult
    next_step: str | None = None

    @staticmethod
    def back() -> "StepOutput":
        return StepOutput(step_result=StepResult.BACK)
    
    @staticmethod
    def next(next_step: str | None = None) -> "StepOutput":
        return StepOutput(
            step_result=StepResult.NEXT,
            next_step=next_step
        )

    @staticmethod
    def stay() -> "StepOutput":
        return StepOutput(step_result=StepResult.STAY)


StateT = TypeVar("StateT")

@dataclass
class HistoryEntry(Generic[StateT]):
    step: str
    state: StateT

class Flow(Generic[StateT]):

    def __init__(
            self,
            steps : dict[str, Callable[[StateT], StepOutput]],
            root: str,
            initial_state : StateT
    ):
        self.steps = steps
        self.current = root
        self.state = initial_state
        self.history : list[HistoryEntry[StateT]] = []

    def run(self) -> None:
        while self.current:
            Flow.save_cursor()
            step = self.steps[self.current]
            res = step(self.state)

            if res.step_result is StepResult.STAY:
                continue

            elif res.step_result is StepResult.BACK:
                self.clear_step()

                if self.history:
                    entry = self.history.pop()
                    self.state = entry.state
                    self.current = entry.step

                else:
                    # Reached the root
                    break

            elif res.step_result is StepResult.NEXT:
                self.history.append(
                    HistoryEntry(
                        step=self.current,
                        state=deepcopy(self.state),
                    )
                )
                self.current = res.next_step

    @staticmethod
    def clear_step():
        Flow.restore_cursor()
        Flow.move_cursor_up()
        Flow.save_cursor()
        Flow.clear_from_cursor()

    @staticmethod
    def move_cursor_up(lines: int = 1):
        sys.stdout.write(ESC + f"{lines}A")
        sys.stdout.flush()

    @staticmethod
    def save_cursor():
        sys.stdout.write(ESC + "s")
        sys.stdout.flush()

    @staticmethod
    def restore_cursor():
        sys.stdout.write(ESC + "u")
        sys.stdout.flush()

    @staticmethod
    def clear_from_cursor():
        sys.stdout.write(ESC + "J")
        sys.stdout.flush()


class ConfigArg(BaseModel):
    """A single command argument as a flag and its optional value."""
    flag: str
    value: str | None = None


@dataclass
class CommandState:
    name : str | None = None
    args : list[ConfigArg] = field(default_factory=list)
    executable : str | None = None
    raw_output : bool = True
    parsed_output_path : Path | None = None
