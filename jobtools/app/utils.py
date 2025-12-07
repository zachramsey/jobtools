from enum import StrEnum
from functools import cache
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor, QGuiApplication
from qt_material import get_theme   # type: ignore


@cache
def get_config_dir() -> str:
    """ Get the path to the JobTools app configuration directory. """
    cfg_path = os.path.join(os.path.dirname(__file__), "configs")
    if not os.path.exists(cfg_path):
        os.makedirs(cfg_path)
    return cfg_path


@cache
def get_resource_dir() -> str:
    """ Get the path to the JobTools app resources directory. """
    dir = os.path.join(os.path.dirname(__file__), "resources")
    if not os.path.exists(dir):
        raise FileNotFoundError(f"Resources directory not found at {dir}.")
    return dir


@cache
def get_sys_theme() -> str:
    """ Get the current system theme (`"light"` or `"dark"`). """
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"
    

@cache
def get_theme_colors() -> dict[str, str]:
    """ Get the current theme's colors as a mapping of names to hex values. """
    res_dir = get_resource_dir()
    theme_name = f"theme_{get_sys_theme()}.xml"
    theme_path = os.path.join(res_dir, theme_name)
    if not os.path.exists(theme_path):
        raise FileNotFoundError(f"Theme {theme_name} not found in resource directory.")
    return get_theme(theme_path)


class ThemeColor(StrEnum):
    PRIMARY = "primaryColor"
    PRIMARY_LIGHT = "primaryLightColor"
    PRIMARY_TEXT = "primaryTextColor"
    SECONDARY = "secondaryColor"
    SECONDARY_LIGHT = "secondaryLightColor"
    SECONDARY_DARK = "secondaryDarkColor"
    SECONDARY_TEXT = "secondaryTextColor"


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
