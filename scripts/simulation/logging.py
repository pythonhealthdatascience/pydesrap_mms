"""Logging.

Logs track events as the code runs - similar to print statements, but keeping a
more permanent record.

Credit:
    > This code is adapted from NHS Digital (2024) RAP repository template
    (https://github.com/NHSDigital/rap-package-template) (MIT Licence).

License:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:
    logger = Sim_Logger(log_to_console=True,
                        log_to_file=True,
                        file_path='../outputs/logs/log.log')
    logger.log('Log message')
"""

import logging
import os
import sys
import time


class Sim_Logger:
    """
    Provides log of events as the simulation runs.

    Attributes:
        log_to_console (boolean):
            Whether to print log messages to the console.
        log_to_file (boolean):
            Whether to save log to a file.
        file_path (str):
            Path to save log to file.
        logger (logging.Logger):
            The logging instance used for logging messages.
    """
    def __init__(self, log_to_console=False, log_to_file=False,
                 file_path=('../outputs/logs/' +
                            f'{time.strftime("%Y-%m-%d_%H-%M-%S")}.log')):
        """
        Initialise the Logger class.

        Arguments:
            log_to_console (boolean):
                Whether to print log messages to the console.
            log_to_file (boolean):
                Whether to save log to a file.
            file_path (str):
                Path to save log to file. Note, if you use an existing .log
                file name, it will append to that log. Defaults to filename
                based on current date and time, and folder '../outputs/log/'.
        """
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.file_path = file_path
        self.logger = None

        # If saving to file, check path is valid
        if self.log_to_file:
            self._validate_log_path()

        # If logging enabled (either printing to console, file or both), then
        # create logger and configure settings
        if self.log_to_console or self.log_to_file:
            self.logger = logging.getLogger(__name__)
            self._configure_logging()

    def _validate_log_path(self):
        """
        Validate the log file path.

        Raises:
            ValueError: If log path is invalid.
        """
        # Check if directory exists
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            raise ValueError(f'The directory "{directory}" for the log ' +
                             'file does not exist.')

        # Check if the file ends with .log
        if not self.file_path.endswith('.log'):
            raise ValueError(f'The log file path "{self.file_path}" must ' +
                             'end with ".log".')

    def _configure_logging(self):
        """
        Configure the logger.
        """
        # Ensure any existing handlers are removed to avoid duplication
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add handlers for saving messages to file and/or printing to console
        handlers = []
        if self.log_to_file:
            handlers.append(logging.FileHandler(self.file_path))
        if self.log_to_console:
            handlers.append(logging.StreamHandler(sys.stdout))

        # Add handlers directly to the logger
        for handler in handlers:
            self.logger.addHandler(handler)

        # Set logging level and format. Level 'INFO' means it's purpose is to
        # confirm things are working as expected.
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:'
            '%(funcName)s():%(lineno)d - %(message)s'
        )
        for handler in handlers:
            handler.setFormatter(formatter)

    def log(self, msg):
        """
        Log a message if logging is enabled.

        Arguments:
            msg (str):
                Message to log.
        """
        if self.log_to_console or self.log_to_file:
            self.logger.info(msg)
