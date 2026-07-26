"""Help theme configuration."""

from __future__ import annotations

from ..colors import BOLD_CYAN, BOLD_GREEN, WHITE, styled


class HelpTheme:
    """Theme for help output formatting."""

    __slots__ = (
        "_color",
        "description",
        "header",
        "metavar",
        "option_string",
        "usage",
    )

    def __init__(
        self,
        usage: str = BOLD_CYAN,
        header: str = BOLD_GREEN,
        option_string: str = BOLD_CYAN,
        metavar: str = BOLD_CYAN,
        description: str = WHITE,
        color: bool = True,
    ):
        self.usage = usage
        self.header = header
        self.option_string = option_string
        self.metavar = metavar
        self.description = description
        self._color = color

    @property
    def color(self) -> bool:
        return self._color

    @color.setter
    def color(self, value: bool) -> None:
        self._color = value

    def apply_style(self, text: str, style: str) -> str:
        return styled(text, style) if self._color else text

    def apply_header(self, text: str) -> str:
        return self.apply_style(text, self.header)

    def apply_usage(self, text: str) -> str:
        return self.apply_style(text, self.usage)

    def apply_option(self, text: str) -> str:
        return self.apply_style(text, self.option_string)

    def apply_metavar(self, text: str) -> str:
        return self.apply_style(text, self.metavar)

    def apply_description(self, text: str) -> str:
        return self.apply_style(text, self.description)
