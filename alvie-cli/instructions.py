from enum import Enum
import re
from pydantic import BaseModel

from InquirerPy.base.control import Choice

class AttackerSection(Enum):
    ISR = "isr"
    PREPARE = "prepare"
    CLEANUP = "cleanup"

class Entity(Enum):
    ENCLAVE = "enclave"
    ATTACKER = "attacker"


class Operand(Enum):
    REGISTER = "reg"
    REGISTER_INDIRECT = "ind"
    MEMORY_LABEL = "mem"
    IMMEDIATE = "imm"
    SECRET = "?"
    IDENT = "ident"

    def is_valid(self, value: str) -> bool:

        if self == Operand.REGISTER:
            num  = value[1:]

            if not num.isdigit():
                return False
            num = int(num)

            return 0 <= num <= 14 and value.startswith("r")
        
        elif self == Operand.REGISTER_INDIRECT:
            num  = value[1:]

            if not num.isdigit():
                return False
            num = int(num)

            return 0 <= num <= 14 and value.startswith("&r")
        
        elif self == Operand.IMMEDIATE:
            # Accepting both X and #X ?
            if value.isdigit():
                return True
            
            num  = value[1:]

            if not num.isdigit():
                return False
            num = int(num)

            return 0 <= num <= 14 and value.startswith("#")
        
        elif self == Operand.MEMORY_LABEL:
            return value.isidentifier()
        
        elif self == Operand.SECRET:
            return value == "?"
        
        elif self == Operand.IDENT:
            ident_rex = re.compile(r"^[A-Za-z0-9_-]+$")
            return bool(ident_rex.fullmatch(value))

        return False

    @staticmethod
    def get_operand_type(value: str) -> "Operand | None":
        try:
            return Operand(value)
        except ValueError:
            return None


class Param(BaseModel):
    operands: list[Operand] = []

class Instruction(BaseModel):
    name: str
    description: str
    params: list[Param] = []
    example: str | None = None
    atom : bool = False

    def get_num_params(self) -> int:
        return len(self.params)

class Combinator(BaseModel):
    name: str
    description: str