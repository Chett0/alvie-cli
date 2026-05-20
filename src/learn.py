from pathlib import Path

from InquirerPy.prompts.list import ListPrompt
from InquirerPy.prompts.input import InputPrompt

required_learn_args = [
    {
        "description" : "Path to attacker specification (.atdl file)",
        "flag" : "--att-spec"
    },
    {
        "description": "Path to enclave specification (.etdl file)",
        "flag" : "--enc-spec"
    }
]

optional_learn_args = [
    {
        "description" : "Output .dot file path for the learned model",
        "flag" : "--res"
    }
]


def learn() -> tuple[bool, list[str]]:
    print("Learning a Mealy machine model...")

    args = []

    for arg in required_learn_args:
        choice = ListPrompt(
            message=f"{arg['description']} (required):",
            choices=[f"Enter {arg['flag']} value", "Back"],
        ).execute()

        if choice == "Back":
            return False, []
        elif choice == f"Enter {arg['flag']} value":
            value = InputPrompt(message=f"Enter value for {arg['flag']}:").execute()
            print(f"Received {arg['flag']} value: {value}")
            args.append(f"{arg['flag']}")
            args.append(value)

    choice = ListPrompt(
        message="Do you want to provide optional arguments?",
        choices=[arg["description"] for arg in optional_learn_args] + ["Done", "Back"],
    ).execute()

        
    return True, args