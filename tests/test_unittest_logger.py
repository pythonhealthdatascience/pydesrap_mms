"""Unit testing for the Logger class.

These check specific parts of the simulation and code, ensuring they work
correctly and as expected.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

from io import StringIO
import logging
import os
from unittest.mock import patch, MagicMock
import pytest
from simulation.logging import SimLogger


def test_log_to_console():
    """
    Confirm that logger.log() prints the provided message to the console.
    """
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        logger = SimLogger(log_to_console=True)
        logger.log(sim_time=None, msg='Test console log')
        # Check if console output matches
        assert 'Test console log' in mock_stdout.getvalue()


def test_log_to_file():
    """
    Confirm that logger.log() would output the message to a .log file at the
    provided file path.
    """
    # Mock the file open operation
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        # Create the logger and log a simple example
        logger = SimLogger(log_to_file=True, file_path='test.log')
        logger.log(sim_time=None, msg='Log message')

        # Check that the file was opened in write mode at the absolute path
        mock_open.assert_called_with(
            os.path.abspath('test.log'), 'w', encoding='locale', errors=None)

        # Verify a FileHandler is attached to the logger
        assert (any(isinstance(handler, logging.FileHandler)
                    for handler in logger.logger.handlers))


def test_invalid_path():
    """
    Ensure there is appropriate error handling for an invalid file path.
    """
    with pytest.raises(ValueError):
        SimLogger(log_to_file=True, file_path='/invalid/path/to/log.log')


def test_invalid_file_extension():
    """
    Ensure there is appropriate error handling for an invalid file extension.
    """
    with pytest.raises(ValueError):
        SimLogger(log_to_file=True, file_path='test.txt')
