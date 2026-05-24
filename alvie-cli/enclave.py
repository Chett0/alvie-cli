from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from pathlib import Path

from utils import BACK_CHOICE, DONE_CHOICE, get_instructions, is_back, is_done
from validators import FileExtensionValidator, ParameterValidator
from instructions import Combinator, Atom, Param, Instruction

def print_enclave(enclave: str, output_path: Path | None = None) -> None:
    print("\nGenerated enclave:\n")
    print(enclave)
    if output_path:
        print(f"Wrote: {output_path}")


def build_instructions(
        instructions : list[Instruction] | list[Atom]
    ) -> str:

    expr : str = ""

    choices : list[Choice] = [
        Choice(value=instr, name=instr.name) for instr in instructions
    ] + [
        BACK_CHOICE
    ]

    # TODO defining atoms'description, parameters and examples

    instr : Instruction = ListPrompt(
        message="Choose atom:",
        choices=choices
    ).execute()

    if is_back(instr):
        return ""

    expr = instr.name

    if instr.name == "ifz":

        add_choice : Choice = Choice(value="add instruction", name="add instruction")
        choices = [
            add_choice,
            DONE_CHOICE
        ]

        def build_sub_expr(atoms: list[Instruction]) -> str:

            expr : str = ""

            while True:

                action : str = ListPrompt(
                    message="Build ifz condition:",
                    choices=choices
                ).execute()

                if is_done(action):
                    if not expr:
                        expr = "eps"
                    break

                if action == add_choice.value:
                    sub_expr = build_instructions(atoms)
                    if expr:
                        expr += f"; {sub_expr}"
                    else:
                        expr = sub_expr

            return expr
        
        # TODO verify if nested ifz instructions isn't allowed even in enclave
        sub_instr : list[Instruction] = [ins for ins in instructions if ins.name != "ifz"]
        left_sub_expr = build_sub_expr(sub_instr)
        right_sub_expr = build_sub_expr(sub_instr)

        expr += f" ({left_sub_expr}) ({right_sub_expr})"

    elif instr.name == "balanced_ifz":

        sub_expr : str | None = None
        add_choice : Choice = Choice(value="add atom", name="add atom")
        choices = [
            add_choice,
            DONE_CHOICE
        ]

        while True:

            action : str = ListPrompt(
                message="Build balanced_ifz condition:",
                choices=choices
            ).execute()

            if is_done(action):
                if not sub_expr:
                    sub_expr = "eps"
                break

            if action == add_choice.value:

                atoms : list[Atom] = [instr for instr in instructions if isinstance(instr, Atom)]
                new_sub_expr = build_instructions(atoms)
                if sub_expr:
                    sub_expr += f"; {new_sub_expr}"
                else:
                    sub_expr = new_sub_expr

        expr += f" ({sub_expr})"

    else:

        atom : Atom | None = instr if isinstance(instr, Atom) else None
        if not atom:
            return expr
        num_params : int = atom.get_num_params()

        if num_params > 0:

            if atom.example:
                print(f"Example: {atom.example}\n")

            params = []

            for i in range(num_params):

                param_validator = ParameterValidator(operand_types=atom.params[i].operands)

                param = InputPrompt(
                    message=f"Parameter {i+1}:",
                    validate=param_validator
                ).execute() 

                params.append(param)

            expr = f"{expr} {', '.join(params)}"

    return expr



def build_combinators(
        combinators : list[Combinator],
        atoms : list[Instruction],
        title: str = "Build enclave body"
    ) -> str:

    expr : str = ""

    choices : list[Choice] = [
            Choice(value=combinator.name, name=combinator.name) for combinator in combinators
        ] + [
            Choice(value="Show", name="show"),
            BACK_CHOICE,
            DONE_CHOICE
        ]

    while True:
        action : str = ListPrompt(
            message=title,
            choices= choices 
        ).execute()

        if is_done(action):
            break

        if is_back(action):
            return ""
        
        if action == "eps":
            if expr:
                expr += f"; eps"
            else:
                expr = "eps"
            
        elif action == "Show":
            enclave_text : str = render_enclave(expr)
            print_enclave(enclave_text)

        elif action == "sequence ;":
            sub_expr : str = build_instructions(atoms)
            if expr:
                expr += f"; {sub_expr}"
            else:
                expr = sub_expr

        elif action == "choice |":
            if not expr:
                left_sub_expr : str = build_combinators(
                    combinators, 
                    atoms, 
                    "Build left side of choice"
                )
                expr = left_sub_expr

            right_sub_expr : str = build_combinators(
                combinators, 
                atoms, 
                "Build right side of choice"
            )

            if right_sub_expr:
                expr = f"{expr} | {right_sub_expr}"

        elif action == "repeat *":
            sub_expr : str = expr if expr else build_instructions(atoms)
            expr = f"({sub_expr})*"

        elif action == "group (...)":
            sub_expr : str = build_combinators(
                combinators, 
                atoms, 
                "Build group expression"
            )
            if expr:
                expr += f"; ({sub_expr})"
            else:
                expr = f"({sub_expr})"

        else:
            raise RuntimeError(f"Unknown action: {action}")

    return expr if expr else "eps"


def render_enclave(body: str) -> str:
    return f"""enclave {{
  {body}
}};
"""


def build_enclave() -> None:

    print("Victim enclave builder\n")

    instructions : dict = get_instructions()
    if not instructions:
        print("No instructions found. Please check the configuration.")
        return
    
    enclave_instructions : dict = instructions.get("enclave", [])
    if not enclave_instructions:
        print("No enclave instructions found. Please check the configuration.")
        return
    
    actions : list = enclave_instructions.get("actions", [])
    if not actions:
        print("No enclave actions found. Please check the configuration.")
        return
    
    # atoms must define params (even if empty) to be correctly validated as Atom instead of Instruction
    actions = [Instruction.model_validate(action) if action.get("params") == None else Atom.model_validate(action) for action in actions]
    
    combinators : list = enclave_instructions.get("combinators", [])
    if not combinators:
        print("No enclave combinators found. Please check the configuration.")
        return

    combinators = [Combinator.model_validate(combinator) for combinator in combinators]

    
    body : str = build_combinators(
        combinators=combinators,
        atoms=actions
    )
    if not body:
        return
    enclave_text : str = render_enclave(body)

    output_path : str = FilePathPrompt(
        message="Output file:",
        default="enclaves/victim.etdl",
        validate=FileExtensionValidator(
            expected_extension=".etdl", 
            must_exists=False
        )
    ).execute()

    Path(output_path).write_text(enclave_text, encoding="utf-8")
    print_enclave(enclave_text, output_path=Path(output_path))


if __name__ == "__main__":
    build_enclave()