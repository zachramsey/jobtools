import re
from enum import StrEnum
from functools import cache
from pathlib import Path
from xml.etree import ElementTree

from PySide6.QtCore import QFile, Qt, QTextStream
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QIcon

from ..resources import rc_resources  # noqa: F401

# --- Directory Utilities ---

@cache
def get_config_dir() -> Path:
    """Get the path to the JobTools app configuration directory."""
    cfg_dir = Path(__file__).parent.parent / "configs"
    if not cfg_dir.exists():
        cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


@cache
def get_data_dir() -> Path:
    """Get the path to the JobTools app data directory."""
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@cache
def get_sys_theme() -> str:
    """Get the current system theme (`"light"` or `"dark"`)."""
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"


def get_stylesheet() -> str:
    """Get the current theme's stylesheet."""
    file = QFile(f":/styles/{get_sys_theme()}.qss")
    if not file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        raise FileNotFoundError("Failed to load stylesheet.")
    stylesheet = QTextStream(file).readAll()
    file.close()
    return stylesheet


def add_font(font_name: str) -> int:
    """Add a font to the application from resources.

    Parameters
    ----------
    font_name : str
        The name of the font file (without extension) located in the resources.

    Returns
    -------
    int
        The ID of the loaded font.
    """
    font_id = QFontDatabase.addApplicationFont(f":/fonts/{font_name}.ttf")
    if font_id == -1:
        raise ValueError(f"Font '{font_name}' could not be loaded.")
    return font_id


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
def get_theme_colors() -> dict[str, str]:
    """Get the current theme's colors as a mapping of names to hex values."""
    file = QFile(f":/colors/{get_sys_theme()}.xml")
    if not file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        raise FileNotFoundError("Failed to load theme colors.")
    xml_str = file.readAll().data().decode()    # type: ignore
    file.close()
    root = ElementTree.fromstring(xml_str)
    colors = {}
    for color in root.findall("color"):
        name = color.get("name")
        value = color.text
        if name and value:
            colors[name] = value
    return colors


@cache
def get_color(color: QColor | ThemeColor | str) -> QColor:
    """Get a color from the current theme.

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


def blend_colors(c1: QColor | ThemeColor | str,
                 c2: QColor | ThemeColor | str,
                 ratio: float = 0.5) -> str:
    """Blend two colors from the current theme.

    Parameters
    ----------
    c1 : ThemeColor or str
        The first color to blend.
    c2 : ThemeColor or str
        The second color to blend.
    ratio : float, optional
        The blend ratio for the first color (0.0 to 1.0). Default is 0.5.

    Returns
    -------
    str
        The blended color as a hex string.
    """
    color1 = get_color(c1)
    color2 = get_color(c2)
    r = int(color1.red() * ratio + color2.red() * (1 - ratio))
    g = int(color1.green() * ratio + color2.green() * (1 - ratio))
    b = int(color1.blue() * ratio + color2.blue() * (1 - ratio))
    return f"#{r:02X}{g:02X}{b:02X}"


def get_icon(icon_name: str, color: QColor | ThemeColor | str | None = None) -> QIcon:
    """Set an icon from the Material Symbols Outlined icon set.

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
    mask = pm.createMaskFromColor(QColor("transparent"), Qt.MaskMode.MaskInColor)
    color = get_color(color or ThemeColor.PRIMARY_TEXT)
    pm.fill(color)
    pm.setMask(mask)
    return QIcon(pm)


# --- Pattern Utilities ---

def build_regex(e: list[str]|str) -> str:
    """Conjunct regex expressions; i.e., `"<expr1>|<expr2>|..."`."""
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
    """Conjunct search expressions; i.e., `"<expr1> AND <expr2> AND ..."`."""
    for i in range(len(e)):
        if any(op in e[i] for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({e[i]})"
        elif " " in e[i]:
            e[i] = f'"{e[i]}"'
    if len(e) == 1:
        return e[0]
    return " AND ".join(e)


def OR(e: list[str]) -> str:
    """Disjunct search expressions; i.e., `"<expr1> OR <expr2> OR ..."`."""
    for i, expr in enumerate(e):
        if any(op in expr for op in ["AND", "OR", "NOT"]):
            if len(e) > 1:
                e[i] = f"({expr})"
        elif " " in expr:
            e[i] = f'"{expr}"'
    if len(e) == 1:
        return e[0]
    return " OR ".join(e)


def NOT(e: str) -> str:
    """Negate a search expression; i.e., `"NOT <expression>"`."""
    if any(op in e for op in ["AND", "OR", "NOT"]):
        e = f"({e})"
    elif " " in e:
        e = f'"{e}"'
    return f"NOT {e}"
