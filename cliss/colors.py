RESET = "\033[0m"

WHITE = "\033[37m"

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
BOLD_CYAN = "\033[1;36m"

_COLORS_ENABLED = True


def set_colors(enabled: bool):
    global _COLORS_ENABLED
    _COLORS_ENABLED = enabled


def is_colors_enabled() -> bool:
    return _COLORS_ENABLED


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
    if is_colors_enabled():
        return BOLD_RED + "Error: " + RESET + text
    else:
        return "Error: " + text


def info(text: str) -> str:
    """Format text as an info message.

    Adds 'Info: ' prefix and colors everything in bold cyan.

    Args:
        text (str): The message content.

    Returns:
        str: Formatted info message.
    """
    if is_colors_enabled():
        return BOLD_CYAN + "Info: " + RESET + text
    else:
        return "Info: " + text
