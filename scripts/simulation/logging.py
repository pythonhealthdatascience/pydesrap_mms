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
    logger = logging.getLogger(__name__)
    logger.info("Performing step X")
"""

import logging
import os
import sys


class Logger:
    """
    Provides log of events as the simulation runs.

    Attributes:
        log_enabled (boolean):
            Enable or disable logging.
        log_path (str):
            Path to the log file.
        log_to_console (boolean):
            Whether to print log messages to the console.
        logger (logging.Logger):
            The logging instance used for logging messages.
    """
    def __init__(self, log_enabled=False, log_path=None, log_to_console=False):
        """
        Initialise the Logger class.

        Arguments:
            log_enabled (boolean):
                Enable or disable logging - defaults to false.
            log_path (str):
                Path to the log file - defaults to none.
            log_to_console (boolean):
                Whether to print log messages to the console as well - defaults
                to false.
        """
        self.log_enabled = log_enabled
        self.log_path = log_path
        self.log_to_console = log_to_console
        self.logger = None

        if self.log_enabled:
            self._validate_log_path()
            self._configure_logging()

    def _validate_log_path(self):
        """
        Validate the log file path.

        Raises:
            ValueError: If log path is invalid.
        """
        # Check if log path is provided
        if not self.log_path:
            raise ValueError('Logging is enabled, but no log_path ' +
                             'is provided.')

        # Check if directory exists
        directory = os.path.dirname(self.log_path)
        if not os.path.exists(directory):
            raise ValueError(f'The directory "{directory}" for the log ' +
                             'file does not exist.')

        # Check if the file ends with .log
        if not self.log_path.endswith('.log'):
            raise ValueError(f'The log file path "{self.log_path}" must ' +
                             'end with ".log".')

    def _configure_logging(self):
        """
        Configure the logger.
        """
        # If wish to print to console, add StreamHandler to handlers
        handlers = [logging.FileHandler(self.log_path)]
        if self.log_to_console:
            handlers.append(logging.StreamHandler(sys.stdout))

        # Define logging settings
        logging.basicConfig(
            # Level INFO means that it's purpose is to confirm things are
            # working as expected
            level=logging.INFO,
            # Format of messages
            format='%(asctime)s - %(levelname)s -- %(filename)s:\
                    %(funcName)5s():%(lineno)s -- %(message)s',
            handlers=handlers
        )

        # Create logger
        self.logger = logging.getLogger(__name__)

    def log(self, msg):
        """
        Log a message if logging is enabled.

        Arguments:
            msg (str):
                Message to log.
        """
        if self.log_enabled:
            self.logger.info(msg)
