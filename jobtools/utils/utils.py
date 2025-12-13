from enum import StrEnum
from functools import cache
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor, QGuiApplication
from qt_material import get_theme   # type: ignore
import re

# --- Directory Utilities ---

@cache
def get_config_dir() -> Path:
    """ Get the path to the JobTools app configuration directory. """
    dir = Path(__file__).parent.parent / "configs"
    if not dir.exists():
        dir.mkdir(parents=True, exist_ok=True)
    return dir


@cache
def get_data_dir() -> Path:
    """ Get the path to the JobTools app data directory. """
    dir = Path(__file__).parent.parent / "data"
    if not dir.exists():
        dir.mkdir(parents=True, exist_ok=True)
    return dir


@cache
def get_resource_dir() -> Path:
    """ Get the path to the JobTools app resources directory. """
    dir = Path(__file__).parent.parent / "resources"
    if not dir.exists():
        raise FileNotFoundError(f"Resources directory not found at {dir}.")
    return dir


def get_data_sources() -> dict[str, Path]:
    """ Get available data sources from the data directory.

    Listed with archive file first, then by date/time in reverse chronological order.

    Returns
    -------
    dict[str, str]
        Mapping of data source labels to their file paths.
    """
    data_dir = get_data_dir()
    sources = {}
    for date in data_dir.iterdir():
        if date.name == "archive":
            sources["Archive"] = date
            continue
        if not date.name.isdigit() or len(date.name) != 8:
            continue
        for time in date.iterdir():
            if not time.name.isdigit() or len(time.name) != 4:
                continue
            for file in time.iterdir():
                if file.suffix == ".csv":
                    year, month, day = date.name[:4], date.name[4:6], date.name[6:8]
                    hour, minute = time.name[:2], time.name[2:4]
                    source_name = f"{year}-{month}-{day} {hour}:{minute}"
                    sources[source_name] = file
    # Sort sources in reverse chronological order
    sources = dict(sorted(sources.items(), reverse=True))
    return sources


# --- Theme Utilities ---

class ThemeColor(StrEnum):
    PRIMARY = "primaryColor"
    PRIMARY_LIGHT = "primaryLightColor"
    PRIMARY_TEXT = "primaryTextColor"
    SECONDARY = "secondaryColor"
    SECONDARY_LIGHT = "secondaryLightColor"
    SECONDARY_DARK = "secondaryDarkColor"
    SECONDARY_TEXT = "secondaryTextColor"


@cache
def get_sys_theme() -> str:
    """ Get the current system theme (`"light"` or `"dark"`). """
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"
    

@cache
def get_theme_colors() -> dict[str, str]:
    """ Get the current theme's colors as a mapping of names to hex values. """
    theme_name = f"theme_{get_sys_theme()}.xml"
    theme_path = get_resource_dir() / theme_name
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme {theme_name} not found in resource directory.")
    return get_theme(str(theme_path))


@cache
def get_color(color: QColor | ThemeColor | str) -> QColor:
    """ Get a color from the current theme.

    Parameters
    ----------
    color : ThemeColor or str
        The theme color to retrieve.
        If a string is provided, it should match one of the ThemeColor values.

    Returns
    -------
    QColor
        The corresponding QColor from the current theme.
    """
    if isinstance(color, QColor):
        pass
    elif isinstance(color, ThemeColor):
        colors = get_theme_colors()
        color = QColor(colors[color.value])
    elif isinstance(color, str):
        try:
            theme_color = ThemeColor(color)
            colors = get_theme_colors()
            color = QColor(colors[theme_color.value])
        except ValueError:
            color = QColor(color)
    return color


def get_icon(icon_name: str, color: QColor | ThemeColor | str | None = None) -> QIcon:
    """ Set an icon from the Material Symbols Outlined icon set.

    Parameters
    ----------
    icon_name : str
        The name of the icon to set.
    color : QColor, str, optional
        The color to apply to the icon.
        May be a QColor, ThemeColor, color name, or hex string.
        If None, uses primary text color from the current theme.

    Returns
    -------
    QIcon
        The configured icon.
    """
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        raise ValueError(f"Icon '{icon_name}' not found in theme.")
    pm = icon.pixmap(1024, 1024)
    mask = pm.createMaskFromColor(QColor('transparent'), Qt.MaskMode.MaskInColor)
    color = get_color(color or ThemeColor.PRIMARY_TEXT)
    pm.fill(color)
    pm.setMask(mask)
    return QIcon(pm)


# --- Pattern Utilities ---

def build_regex(e: list[str]|str) -> str:
    """ Conjunct regex expressions; i.e., `"<expr1>|<expr2>|..."`. """
    if isinstance(e, str):
        e = [e]
    _e = []
    for expr in e:
        expr = expr.strip()
        if expr:
            _e.append(re.escape(expr.lower()))
    if len(_e) == 1:
        return _e[0]
    return "|".join(_e)


def AND(e: list[str]) -> str:
    """ Conjunct search expressions; i.e., `"<expr1> AND <expr2> AND ..."`. """
    for i in range(len(e)):
        if any(op in e[i] for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({e[i]})"
        elif " " in e[i]:
            e[i] = f"\"{e[i]}\""
    if len(e) == 1:
        return e[0]
    return " AND ".join(e)


def OR(e: list[str]) -> str:
    """ Disjunct search expressions; i.e., `"<expr1> OR <expr2> OR ..."`. """
    for i, expr in enumerate(e):
        if any(op in expr for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({expr})"
        elif " " in expr:
            e[i] = f"\"{expr}\""
    if len(e) == 1:
        return e[0]
    return " OR ".join(e)


def NOT(e: str) -> str:
    """ Negate a search expression; i.e., `"NOT <expression>"`. """
    if any(op in e for op in ["AND", "OR", "NOT"]):
        e = f"({e})"
    elif " " in e:
        e = f"\"{e}\""
    return f"NOT {e}"
