import sys

from cli import run_interactive, run_non_interactive

def main() -> None:
    try:
        if len(sys.argv) == 1:
            run_interactive()
        else:
            run_non_interactive(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
