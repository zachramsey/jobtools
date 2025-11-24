import logging


class JTLogger:
    formatter = logging.Formatter(
        "{asctime} | {name:^8} | {levelname:^8} | {message}",
        datefmt="%H:%M:%S",
        style="{"
    )

    def __init__(self):
        self.logger = logging.getLogger("JobTools")

    def configure(self, level):
        self.set_level(level)
        self._add_handler()
        self.logger.propagate = False

    def debug(self, message):
        self.logger.debug(f"{message}")

    def info(self, message):
        self.logger.info(f"{message}")

    def warning(self, message):
        self.logger.warning(f"{message}")
    
    def set_level(self, level):
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level in levels:
            self.logger.setLevel(level)

    def _add_handler(self):
        sh = logging.StreamHandler()
        sh.setFormatter(self.formatter)
        self.logger.addHandler(sh)

        # Remove duplicate handlers
        if len(self.logger.handlers) > 1:
            self.logger.handlers = [self.logger.handlers[0]]

    @staticmethod
    def conform_format(logger_name: str):
        """ Set JTLogger format for an existing logger by name. """
        logger = logging.getLogger(logger_name)
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setFormatter(JTLogger.formatter)
                break