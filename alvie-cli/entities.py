from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice
from InquirerPy.prompts.fuzzy import FuzzyPrompt

from pathlib import Path
import os

from utils import BACK_CHOICE, DONE_CHOICE, HELP_CHOICE, SHOW_CHOICE, is_back, is_done, is_help, is_show, load_combinators, load_instructions
from validators import FileExtensionValidator, ParameterValidator, ChoiceValidator
from instructions import AttackerSection, Combinator, Entity, Instruction

from commands import Command

def print_entity(
        entity: str, 
        output_path: Path | None = None
    ) -> None:
    print("\nGenerated entity:\n")
    print(entity)
    if output_path:
        print(f"Saved in: {output_path}\n")

# A global variable that defines if using description or not?
# TODO refactor with a superclass BaseChoice
def build_choices(
        items : list[Combinator] | list[Instruction] | list[Command],
        extra_choices : list[Choice] = [],
        include_desc : bool = False
    ) -> list[Choice]:
    """
    Build a list of choices for the given list of combinators or instructions

    Args:
        items: list of combinators or instructions to build choices from
        extra_choices: list of extra choices to include in the returned list of choices
        include_desc: whether to include the description of the combinators/instructions in the choice name
    """

    if include_desc:
        choices = [
            *map(lambda item: Choice(value=item, name=f"{item.name} - {item.description}"), items),
            *extra_choices
        ]
    else:
        choices = [
            *map(lambda item: Choice(value=item, name=item.name), items),
            *extra_choices
        ]

    return choices

def build_instructions(
        instructions : list[Instruction],
        message = "Choose instruction:",
        help=False
    ) -> str:

    expr : str = ""

    extra_choices : list[Choice] = [] 
    if not help:
        extra_choices.append(HELP_CHOICE)
    extra_choices.append(BACK_CHOICE)

    choices = build_choices(
        items=instructions,
        extra_choices=extra_choices,
        include_desc=help
    )

    instr : Instruction = FuzzyPrompt(
        message=message,
        choices=choices,
        max_height="70%",
        validate=ChoiceValidator(choices=choices),
        invalid_message="Please select a valid instruction from the list"
    ).execute()

    if is_back(instr):
        return ""
    
    if is_help(instr):
        sub_expr = build_instructions(
            instructions=instructions,
            message="Choose instruction:",
            help=True
        )

        if expr:
            if sub_expr:
                expr += f"; {sub_expr}"
        else:
            expr = sub_expr
        return expr

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
                    sub_expr += f";\n {new_sub_expr}"
                else:
                    sub_expr = new_sub_expr

        expr += f" ({sub_expr})"

    else:
        num_params : int = instr.get_num_params()

        if num_params > 0:

            if instr.examples:
                print(f"Examples:")
                for example in instr.examples:
                    print(f"  - {instr.name} {example}")
                print()

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
        section: str = "enclave",
        help=False
    ) -> str:

    expr : str = ""

    extra_choices: list[Choice] = []
    if not help:
        extra_choices.append(HELP_CHOICE)
    extra_choices.extend([SHOW_CHOICE, BACK_CHOICE, DONE_CHOICE])

    choices = build_choices(
        items=combinators,
        extra_choices=extra_choices,
        include_desc=help
    )

    while True:
        action = FuzzyPrompt(
            message=f"Build {section} body",
            choices= choices,
            max_height="70%",
            validate=ChoiceValidator(choices=choices),
            invalid_message="Please select a valid instruction from the list"
        ).execute()

        if is_done(action):
            break

        if is_back(action):
            return ""

        if is_help(action):
            sub_expr = build_combinators(
                combinators=combinators,
                atoms=atoms,
                section=section,
                help=True
            )

            if expr:
                if sub_expr != "eps":
                    expr += f"; {sub_expr}"
            else:
                expr = sub_expr
            return expr
        
        if is_show(action):
            print(f"\nCurrent expression:\n{expr}\n")
            continue
        
        match action.name:
            case "eps":
                if expr:
                    expr += f";\n eps"
                else:
                    expr = "eps"

            case "sequence ;":
                sub_expr : str = build_instructions(atoms)
                if expr:
                    expr += f";\n {sub_expr}"
                else:
                    expr = sub_expr
            # TODO: it shows prepare body twice for attacker 
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
                        expr += f";\n ({sub_expr})"
                    else:
                        expr = f"({sub_expr})"

            case _:
                raise RuntimeError(f"Unknown action: {action}")

    return expr if expr else "eps"

def get_combinators_actions(
        type : Entity
    ) -> tuple[list[Combinator], list[Instruction]]:
    
    # get combinators
    raw_combinators : list = load_combinators()
    if not raw_combinators:
        raise RuntimeError("No entity combinators found. Please check the configuration.")
    combinators : list[Combinator] = [
        Combinator.model_validate(combinator) 
        for combinator in raw_combinators
    ]

    # get instructions
    instructions : dict = load_instructions()
    if not instructions:
        raise RuntimeError("No instructions found. Please check the configuration.")
    
    actions : list[Instruction] = [
        Instruction.model_validate(action)
        for action in instructions
        if type.value in action.get("available_for", [])
    ]
    
    # entity_instructions : dict = instructions.get(type.value, [])
    # if not entity_instructions:
    #     raise RuntimeError("No entity instructions found. Please check the configuration.")
    
    # raw_actions : list = entity_instructions.get("actions", [])
    # if not raw_actions:
    #     raise RuntimeError("No entity actions found. Please check the configuration.")
    
    # actions : list[Instruction] = [Instruction.model_validate(action) for action in raw_actions]

    return combinators, actions


def save_entity(
        text : str,
        default: str,
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
    
    while True:
        
        output_path : str = FilePathPrompt(
            message="Output file:",
            default=default,
            validate=file_extension_validator
        ).execute()
        path = Path(output_path)
        
        if path.exists():
            overwrite = ListPrompt(
                message="File already exists. Overwrite?",
                choices=[
                    Choice(value=True, name="yes"),
                    Choice(value=False, name="no")
                ]
            ).execute()

            if not overwrite:
                print("Please choose another file name.")
                continue
            
        path.parent.mkdir(parents=True, exist_ok=True)
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

    print("Victim enclave builder\n")

    combinators, actions = get_combinators_actions(type=Entity.ENCLAVE)
    
    body : str = build_combinators(
        combinators=combinators,
        atoms=actions
    )
    if not body:
        return
    enclave_text : str = render_section(body, title="enclave")

    WORKING_PATH = os.environ["WORKING_PATH"]
    output_path : Path | None = save_entity(
        text=enclave_text,
        default=f"{WORKING_PATH}/enclaves/victim.etdl",
        file_extension_validator=FileExtensionValidator.enclave_file_validator()
    )

    print_entity(
        entity=enclave_text, 
        output_path=output_path
    )


def build_attacker() -> None:
    
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

    WORKING_PATH = os.environ["WORKING_PATH"]
    output_path : Path | None = save_entity(
        text=attacker_text,
        default=f"{WORKING_PATH}/attackers/attacker.atdl",
        file_extension_validator=FileExtensionValidator.attacker_file_validator()
    )

    print_entity(
        entity=attacker_text, 
        output_path=output_path
    )