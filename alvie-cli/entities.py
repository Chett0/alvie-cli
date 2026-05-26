from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from pathlib import Path

from utils import BACK_CHOICE, DONE_CHOICE, get_instructions, is_back, is_done
from validators import FileExtensionValidator, ParameterValidator
from instructions import Combinator, AttackerSection, Entity, Instruction

def print_entity(
        entity: str, 
        output_path: Path | None = None
    ) -> None:
    print("\nGenerated entity:\n")
    print(entity)
    if output_path:
        print(f"Wrote: {output_path}")


def build_instructions(
        instructions : list[Instruction],
        message = "Choose instruction:"
    ) -> str:

    expr : str = ""

    choices : list[Choice] = [
        Choice(value=instr, name=instr.name) for instr in instructions
    ] + [
        BACK_CHOICE
    ]

    instr : Instruction = ListPrompt(
        message=message,
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

                atoms : list[Instruction] = [instr for instr in instructions if instr.atom]
                new_sub_expr = build_instructions(
                    atoms,
                    message="Choose atom:"
                )
                if sub_expr:
                    sub_expr += f"; {new_sub_expr}"
                else:
                    sub_expr = new_sub_expr

        expr += f" ({sub_expr})"

    else:
        num_params : int = instr.get_num_params()

        if num_params > 0:

            if instr.example:
                print(f"Example: {instr.example}\n")

            params = []

            for i in range(num_params):

                param_validator = ParameterValidator(operand_types=instr.params[i].operands)

                param = InputPrompt(
                    message=f"Parameter {i+1}:",
                    validate=param_validator
                ).execute() 

                params.append(param)

            if instr.name == "create":
                expr = f"{expr} <{', '.join(params)}>"
            else:
                expr = f"{expr} {', '.join(params)}"

    return expr



def build_combinators(
        combinators : list[Combinator],
        atoms : list[Instruction],
        section: str = "enclave"
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
            message=f"Build {section} body",
            choices= choices 
        ).execute()

        if is_done(action):
            break

        if is_back(action):
            return ""
        
        match action:
            case "eps":
                if expr:
                    expr += f"; eps"
                else:
                    expr = "eps"
            
            case "Show":
                print(f"\nCurrent expression:\n{expr}\n")

            case "sequence ;":
                sub_expr : str = build_instructions(atoms)
                if expr:
                    expr += f"; {sub_expr}"
                else:
                    expr = sub_expr

            case "choice |":
                if not expr:
                    left_sub_expr : str = build_combinators(
                        combinators, 
                        atoms, 
                        "Build left side of choice"
                    )
                    expr = left_sub_expr

                if expr:
                    right_sub_expr : str = build_combinators(
                        combinators, 
                        atoms, 
                        "Build right side of choice"
                    )

                    if right_sub_expr:
                        expr = f"{expr} | {right_sub_expr}"

            case "repeat *":
                sub_expr : str = expr if expr else build_instructions(atoms)
                if sub_expr:
                    expr = f"({sub_expr})*"

            case "group (...)":
                sub_expr : str = build_combinators(
                    combinators, 
                    atoms, 
                    "Build group expression"
                )
                if sub_expr:
                    if expr:
                        expr += f"; ({sub_expr})"
                    else:
                        expr = f"({sub_expr})"

            case _:
                raise RuntimeError(f"Unknown action: {action}")

    return expr if expr else "eps"

def get_combinators_actions(
        type : Entity
    ) -> tuple[list[Combinator], list[Instruction]]:

    instructions : dict = get_instructions()
    if not instructions:
        raise RuntimeError("No instructions found. Please check the configuration.")
    
    entity_instructions : dict = instructions.get(type.value, [])
    if not entity_instructions:
        raise RuntimeError("No entity instructions found. Please check the configuration.")
    
    raw_actions : list = entity_instructions.get("actions", [])
    if not raw_actions:
        raise RuntimeError("No entity actions found. Please check the configuration.")
    
    actions : list[Instruction] = [Instruction.model_validate(action) for action in raw_actions]
    
    raw_combinators : list = entity_instructions.get("combinators", [])
    if not raw_combinators:
        raise RuntimeError("No entity combinators found. Please check the configuration.")

    combinators : list[Combinator] = [Combinator.model_validate(combinator) for combinator in raw_combinators]

    return combinators, actions


def save_entity(
        text : str,
        file_extension_validator : FileExtensionValidator,
) -> Path | None: 
    
    save = ListPrompt(
        message="Save generated entity?",
        choices=[
            Choice(value=True, name="yes"),
            Choice(value=False, name="no")
        ]
    ).execute()

    if not save:
        return None
    
    output_path : str = FilePathPrompt(
        message="Output file:",
        default="enclaves/victim.etdl",
        validate=file_extension_validator
    ).execute()

    path = Path(output_path)
    path.write_text(text, encoding="utf-8")
    return path


def render_section(
        body: str,
        title: str
    ) -> str:
    return f"""{title} {{
  {body}
}};
"""
    

def build_enclave() -> None:

    # TODO define enclave instructions in json config

    print("Victim enclave builder\n")

    combinators, actions = get_combinators_actions(type=Entity.ENCLAVE)
    
    body : str = build_combinators(
        combinators=combinators,
        atoms=actions
    )
    if not body:
        return
    enclave_text : str = render_section(body, title="enclave")

    output_path : Path | None = save_entity(
        text=enclave_text,
        file_extension_validator=FileExtensionValidator.enclave_file_validator()
    )

    print_entity(
        entity=enclave_text, 
        output_path=output_path
    )


def build_attacker() -> None:

    # TODO define attacker instructions in json config
    # TODO maybe split atoms and combinators in json config because they are the same for enclave and attacker?

    print("Attacker builder\n")

    combinators, actions = get_combinators_actions(type=Entity.ATTACKER)
    section_texts : list[str] = []

    for section in AttackerSection:
        section_body : str = build_combinators(
            combinators=combinators,
            atoms=actions,
            section=section.value
        )
        if not section_body:
            return
        section_text : str = render_section(section_body, title=section.value)
        section_texts.append(section_text)

    attacker_text : str = "\n".join(section_texts)

    output_path : Path | None = save_entity(
        text=attacker_text,
        file_extension_validator=FileExtensionValidator.attacker_file_validator()
    )

    print_entity(
        entity=attacker_text, 
        output_path=output_path
    )