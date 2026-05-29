from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice

from entities import Entity
from executions import execute
    

def main():
    print("\nWelcome to the Alvie CLI!\n")
    
    while True:
        choice = ListPrompt(
            message="What do you want to do:",
            choices=[
                Choice(value="execute", name="Execute a command") 
            ] + [
                Choice(value=entity, name=f"Build {entity.value}")
                for entity in Entity
            ] + [
                Choice(value="exit", name="Exit")
            ]
        ).execute()

        if choice == "execute":
            execute()
        elif choice == "exit":
            return
        else:
            choice.build()


if __name__ == "__main__":
    main()
