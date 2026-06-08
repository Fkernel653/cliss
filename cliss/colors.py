RESET = "\033[0m"

WHITE = "\033[37m"

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
BOLD_CYAN = "\033[1;36m"


def styled(text: str, color: str) -> str:
    """Wrap text in ANSI color code and add reset.

    Args:
        text (str): The text to color.
        color (str): ANSI color code (e.g., BOLD_GREEN, GRAY).

    Returns:
        str: Colored text followed by reset formatting.
    """
    return color + text + RESET


def error(text: str) -> str:
    """Format text as an error message.

    Adds 'Error: ' prefix and colors everything in bold red.

    Args:
        text (str): The message content.

    Returns:
        str: Formatted error message.
    """
    return BOLD_RED + "Error: " + RESET + text


def info(text: str) -> str:
    """Format text as an info message.

    Adds 'Info: ' prefix and colors everything in bold cyan.

    Args:
        text (str): The message content.

    Returns:
        str: Formatted info message.
    """
    return BOLD_CYAN + "Info: " + RESET + text
