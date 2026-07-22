from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommandArgument(BaseModel):
    flag: str
    value: str | None = None


class StepInput(BaseModel):
    symbol: str
    actor: str


class RunStep(BaseModel):
    inputs: list[StepInput]
    outputs: list[str]


class Recap(BaseModel):
    model_config = ConfigDict(extra="allow")

    hypotheses: int
    runs: int
    steps: int


class ParsedOutputData(BaseModel):
    executable: str
    args: list[CommandArgument]
    start: str
    end: str
    recap: Recap
    hypotheses: list[list[list[RunStep]]]


class ParsedOutputCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    data: ParsedOutputData


class ParsedOutputUpdate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


class ParsedOutputSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    executable: str
    start: str
    end: str
    created_at: datetime


class ParsedOutputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    created_at: datetime
    data: dict
