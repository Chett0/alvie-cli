import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

LOGO_LINES = [
    " █████╗  ██╗     ██╗   ██╗ ██╗ ███████╗",
    "██╔══██╗ ██║     ██║   ██║ ██║ ██╔════╝",
    "███████║ ██║     ██║   ██║ ██║ █████╗  ",
    "██╔══██║ ██║     ╚██╗ ██╔╝ ██║ ██╔══╝  ",
    "██║  ██║ ███████╗ ╚████╔╝  ██║ ███████╗",
    "╚═╝  ╚═╝ ╚══════╝  ╚═══╝   ╚═╝ ╚══════╝",
]

# Gradient endpoints (blue -> cyan).
GRADIENT_START = (80, 150, 255)
GRADIENT_END = (110, 230, 220)

TAGLINE = "Interface for the Alvie analysis tool"
TIP = "Pick an action below  ·  Ctrl+C to exit"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _truecolor(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _gradient_line(text: str, ratio: float) -> str:
    sr, sg, sb = GRADIENT_START
    er, eg, eb = GRADIENT_END
    r = round(sr + (er - sr) * ratio)
    g = round(sg + (eg - sg) * ratio)
    b = round(sb + (eb - sb) * ratio)
    return f"{BOLD}{_truecolor(r, g, b)}{text}{RESET}"


def print_banner() -> None:
    color = _supports_color()
    width = max(len(line) for line in LOGO_LINES)
    pad = "  "

    print()
    for i, line in enumerate(LOGO_LINES):
        ratio = i / (len(LOGO_LINES) - 1)
        rendered = _gradient_line(line, ratio) if color else line
        print(f"{pad}{rendered}")
    print()

    # Rounded info box, sized to the widest content line (logo or text).
    box_texts = ["✻ Welcome to Alvie CLI", "", TAGLINE, TIP]
    inner = max(width, *(len(t) for t in box_texts))
    top = f"╭{'─' * (inner + 2)}╮"
    bottom = f"╰{'─' * (inner + 2)}╯"

    def box_line(text: str, *, accent: bool = False) -> str:
        body = f"│ {text.ljust(inner)} │"
        if not color:
            return f"{pad}{body}"
        style = BOLD if accent else DIM
        return f"{pad}{DIM}│{RESET} {style}{text.ljust(inner)}{RESET} {DIM}│{RESET}"

    edge = f"{pad}{DIM}{top}{RESET}" if color else f"{pad}{top}"
    edge_b = f"{pad}{DIM}{bottom}{RESET}" if color else f"{pad}{bottom}"

    print(edge)
    print(box_line("✻ Welcome to Alvie CLI", accent=True))
    print(box_line(""))
    print(box_line(TAGLINE))
    print(box_line(TIP))
    print(edge_b)
    print()
