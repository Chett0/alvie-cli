from dataclasses import dataclass, field


@dataclass # generate init, eq, repr automatically
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


@dataclass
class ParsedRun:
    steps: list[ParsedStep] = field(default_factory=list)

    def to_dict(self) -> list[dict]:
        return [step.to_dict() for step in self.steps]


@dataclass
class ParsedHypothesis:
    runs: list[ParsedRun] = field(default_factory=list)

    def to_dict(self) -> list[dict]:
        return [run.to_dict() for run in self.runs]
