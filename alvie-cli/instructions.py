from enum import Enum
import re
from pydantic import BaseModel

class Entity(Enum):
    ENCLAVE     = "enclave"
    ATTACKER    = "attacker"

class AttackerSection(Enum):
    ISR = "isr"
    PREPARE = "prepare"
    CLEANUP = "cleanup"


class Operand(Enum):
    REGISTER        = "reg"        # rX, 0 <= X <= 14
    MEMORY_LABEL    = "label"      # [a-zA-Z_][a-zA-Z0-9_]*
    REG_ADDRESS     = "reg_addr"   # &rX
    LABEL_ADDRESS   = "label_addr" # &label
    DEREF           = "deref"      # @rX
    IMMEDIATE       = "imm"        # #<number> || #label
    SECRET          = "?"          # ?
    IDENT           = "ident"      # [A-Za-z0-9_-]+
    INT             = "int"        # n, n >= 0

    def is_valid(self, value: str) -> bool:
        
        match self:
            case Operand.REGISTER:
                return self.is_register(value)
            case Operand.MEMORY_LABEL:
                return self.is_label(value)
            case Operand.REG_ADDRESS:
                return self.is_reg_address(value)
            case Operand.LABEL_ADDRESS:
                return self.is_label_address(value)
            case Operand.DEREF:
                return self.is_deref(value)
            case Operand.IMMEDIATE:
                return self.is_immediate(value)
            case Operand.SECRET:
                return self.is_secret(value)
            case Operand.IDENT:
                return self.is_ident(value)
            case Operand.INT:
                return self.is_positive_int(value)
            case _:
                raise ValueError(f"Unknown operand type: {self.value}")

    # Register --> r{0-14}
    def is_register(self, value: str) -> bool:
        
        if not value.startswith("r"):
            return False
        
        num = value[1:]
        
        if not num.isdigit():
            return False
        num = int(num)
        
        return 0 <= num <= 14
    
    # Label --> [a-zA-Z_][a-zA-Z0-9_]*
    def is_label(self, value: str) -> bool:
        return value.isidentifier()
    
    # Immediate --> #<number> || #label
    def is_immediate(self, value: str) -> bool:
        
        if not value.startswith("#"):
            return False
        
        target = value[1:]
        
        return (
            self.is_positive_int(target) or
            self.is_label(target)
        )
    
    # Register Address --> &rX
    def is_reg_address(self, value: str) -> bool:
        if not value.startswith("&"):
            return False
        
        target = value[1:]
        return self.is_register(target)
    
    # Label Address --> &label
    def is_label_address(self, value: str) -> bool:
        if not value.startswith("&"):
            return False
        
        target = value[1:]
        return self.is_label(target)
    
    # Deref --> @rX
    def is_deref(self, value: str) -> bool:
        if not value.startswith("@"):
            return False
        
        target = value[1:]
        return self.is_register(target)

    # Secret --> ?
    def is_secret(self, value: str) -> bool:
        return value == "?"
    
    def is_ident(self, value: str) -> bool:
        ident_rex = re.compile(r"^[A-Za-z0-9_-]+$")
        return bool(ident_rex.fullmatch(value))
    
    def is_positive_int(self, value: str) -> bool:
        # is <n> one byte? 
        return value.isdigit() and int(value) >= 0

    @staticmethod
    def get_operand_type(value: str) -> "Operand | None":
        try:
            return Operand(value)
        except ValueError:
            return None



# Source --> reg || DEREF || LABEL_ADDRESS || imm || ?
SOURCE_OPERANDS = {
    Operand.REGISTER,
    Operand.DEREF,
    Operand.LABEL_ADDRESS,
    Operand.IMMEDIATE,
    Operand.SECRET
}


# Destination --> reg || REG_ADDRESS || LABEL_ADDRESS
DEST_OPERANDS = {
    Operand.REGISTER,
    Operand.REG_ADDRESS,
    Operand.LABEL_ADDRESS
}

class Param(BaseModel):
    operands: list[Operand] = []

class Instruction(BaseModel):
    name: str
    description: str
    params: list[Param] = []
    examples: list[str] | None = None
    atom : bool = False
    available_for: list[Entity] = []

    def get_num_params(self) -> int:
        return len(self.params)

class Combinator(BaseModel):
    name: str
    description: str