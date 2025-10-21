class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def print_colored(text, color):
    print(f"{color}{text}{Color.RESET}")
