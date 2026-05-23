from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.filepath import FilePathPrompt
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from pathlib import Path
from utils import get_instructions
from validators import FileExtensionValidator

def print_enclave(enclave: str, output_path: Path | None = None) -> None:
    print("\nGenerated enclave:\n")
    print(enclave)
    if output_path:
        print(f"Wrote: {output_path}")


def build_atoms(
        atoms : dict
    ) -> str:

    expr = ""

    choices = [
        Choice(value=atom, name=atom["name"]) for atom in atoms
    ] + [
        Choice(value="Back", name="back")
    ]

    atom = ListPrompt(
        message="Choose atom:",
        choices=choices
    ).execute()

    if atom == "Back":
        return ""

    expr = atom["name"]
    atom_num_params = atom.get("num_params", 0)
    
    # TODO handle list parameters (see ifz, balanced_fiz)

    if atom_num_params > 0:

        atom_example = atom.get("example", None)
        if atom_example:
            print(f"Example: {atom_example}\n")

        params = []

        for i in range(atom_num_params):

            param = InputPrompt(
                message=f"Parameter {i+1}:"
            ).execute()

            # TODO validate parameter based on atom specification
            # TODO handle ? parameter 

            params.append(param)

        expr = f"{expr} {', '.join(params)}"

    return expr



def build_instruction_list(
        combinators : dict,
        atoms : dict,
        title: str = "Build enclave body"
    ) -> str:

    expr = ""

    choices = [
            Choice(value=combinator["name"], name=combinator["name"]) for combinator in combinators
        ] + [
            Choice(value="Show", name="show"),
            Choice(value="Back", name="back"),
            Choice(value="Done", name="done")
        ]

    while True:
        action = ListPrompt(
            message=title,
            choices= choices 
        ).execute()

        if action == "Done":
            break

        if action == "Back":
            return ""
        
        if action == "eps":
            if expr:
                expr += f"; eps"
            else:
                expr = "eps"
            
        elif action == "Show":
            enclave_text = render_enclave(expr)
            print_enclave(enclave_text)

        elif action == "sequence ;":
            sub_expr = build_atoms(atoms)
            if expr:
                expr += f"; {sub_expr}"
            else:
                expr = sub_expr

        elif action == "choice |":
            if not expr:
                left_sub_expr = build_instruction_list(
                    combinators, 
                    atoms, 
                    "Build left side of choice"
                )
                expr = left_sub_expr

            right_sub_expr = build_instruction_list(
                combinators, 
                atoms, 
                "Build right side of choice"
            )

            if right_sub_expr:
                expr = f"{expr} | {right_sub_expr}"

        elif action == "repeat *":
            sub_expr = expr if expr else build_atoms(atoms)
            expr = f"({sub_expr})*"

        elif action == "group (...)":
            sub_expr = build_instruction_list(
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

    instructions = get_instructions()
    if not instructions:
        print("No instructions found. Please check the configuration.")
        return
    
    enclave_instructions = instructions.get("enclave", [])
    if not enclave_instructions:
        print("No enclave instructions found. Please check the configuration.")
        return
    
    atoms = enclave_instructions.get("atoms", [])
    if not atoms:
        print("No enclave atoms found. Please check the configuration.")
        return
    
    combinators = enclave_instructions.get("combinators", [])
    if not combinators:
        print("No enclave combinators found. Please check the configuration.")
        return

    
    body = build_instruction_list(
        combinators=combinators,
        atoms=atoms
    )
    if not body:
        return
    enclave_text = render_enclave(body)

    output_path = FilePathPrompt(
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