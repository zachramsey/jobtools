import logging


class JDLogger:
    _formatter = logging.Formatter(
        "{asctime} | {name:^8} | {levelname:^8} | {message}",
        datefmt="%H:%M:%S",
        style="{"
    )

    def __init__(self):
        """ Get the JobData logger instance. """
        self.logger = logging.getLogger("JobTools")

    def configure(self, level):
        """ Configure the JDLogger instance. """
        self.set_level(level)
        self.addHandler(logging.StreamHandler())
        self.logger.propagate = False

    def debug(self, message):
        """ Log a debug-level message. """
        self.logger.debug(f"{message}")

    def info(self, message):
        """ Log an info-level message. """
        self.logger.info(f"{message}")

    def warning(self, message):
        """ Log a warning-level message. """
        self.logger.warning(f"{message}")

    def error(self, message):
        """ Log an error-level message. """
        self.logger.error(f"{message}")

    def set_level(self, level):
        """ Set the logging level. """
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level in levels:
            self.logger.setLevel(level)

    def addHandler(self, handler: logging.Handler):
        """ Add the specified handler to the
        JobData logger and set its formatter. """
        handler.setFormatter(self._formatter)
        self.logger.addHandler(handler)

    # def _add_sh_handler(self):
    #     sh = logging.StreamHandler()
    #     sh.setFormatter(self._formatter)
    #     self.logger.addHandler(sh)

    #     # Remove duplicate handlers
    #     if len(self.logger.handlers) > 1:
    #         self.logger.handlers = [self.logger.handlers[0]]

    @staticmethod
    def conform_format(logger_name: str):
        """ Set JDLogger format for an existing logger by name. """
        logger = logging.getLogger(logger_name)
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setFormatter(JDLogger._formatter)
                break