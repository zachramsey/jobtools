from pathlib import Path
from subprocess import run

import PySide6  # noqa: F401
from qt_material import export_theme  # type: ignore

if __name__ == "__main__":
    cwd = Path(__file__).parent
    (cwd / "styles").mkdir(exist_ok=True)

    extra_base = {
        "font_size": "14px",
        "line_height": "14px",
        "density_scale": "0",
        "pyside6": True,
        "linux": True,
    }

    # Export light theme
    light_extra = {"danger": "#DB3E03", "warning": "#977100", "success": "#008679"}
    light_extra.update(extra_base)  # type: ignore
    export_theme(theme=str(cwd / "colors" / "light.xml"),
                 qss=str(cwd / "styles" / "light.qss"),
                #  rcc=str(cwd / "collections" / "icons_light.qrc"),
                 extra=light_extra,
                 output=str(cwd / "icons_light"))

    # Export dark theme
    dark_extra = {"danger": "#FF8B69", "warning": "#D8A300", "success": "#48BDAE"}
    dark_extra.update(extra_base)   # type: ignore
    export_theme(theme=str(cwd / "colors" / "dark.xml"),
                 qss=str(cwd / "styles" / "dark.qss"),
                #  rcc=str(cwd / "collections" / "icons_dark.qrc"),
                 extra=dark_extra,
                 output=str(cwd / "icons_dark"))

    # Build resource files
    run(["pyside6-rcc", "icons_light.qrc", "-o", "rc_icons_light.py"], cwd=cwd)
    run(["pyside6-rcc", "icons_dark.qrc", "-o", "rc_icons_dark.py"], cwd=cwd)
    run(["pyside6-rcc", "resources.qrc", "-o", "rc_resources.py"], cwd=cwd)
