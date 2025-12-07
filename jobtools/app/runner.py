from PySide6.QtWidgets import QWidget
from .utils import get_config_dir


class SaveConfig(QWidget):
    """ Save the current configuration to a file. """

    def __init__(self):
        super().__init__()
        self._config_dir = get_config_dir()


class LoadConfig(QWidget):
    """ Select and load a configuration file. """

    def __init__(self):
        super().__init__()
        self._config_dir = get_config_dir()


class RunCollector(QWidget):
    """ Run data collection with the current configuration. """

    def __init__(self):
        super().__init__()


class RunnerPage(QWidget):
    """ Page for running JobTools operations. """

    def __init__(self):
        super().__init__()
