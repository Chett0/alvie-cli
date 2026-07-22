from InquirerPy.base.control import Choice

DONE_CHOICE : Choice = Choice(value="Done", name="[✓] Done")
BACK_CHOICE : Choice = Choice(value="Back", name="[←] Back")
HELP_CHOICE : Choice = Choice(value="Help", name="[?] Help")
SHOW_CHOICE : Choice = Choice(value="Show", name="[~] Show")

def is_done(value) -> bool:
    return value == DONE_CHOICE.value

def is_back(value) -> bool:
    return value == BACK_CHOICE.value

def is_help(value) -> bool:
    return value == HELP_CHOICE.value

def is_show(value) -> bool:
    return value == SHOW_CHOICE.value