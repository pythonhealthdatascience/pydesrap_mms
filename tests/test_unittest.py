"""
Unit testing

SimPy itself has lots of tests of the SimPy components themselves, as can view:
https://gitlab.com/team-simpy/simpy/-/tree/master/tests?ref_type=heads.
Hence, our focus here is testing components we have written ourselves.
"""

from io import StringIO
import logging
import os
from unittest.mock import patch, MagicMock

import pytest

from simulation import Model, Param, SimLogger


def test_new_attribute():
    """
    Confirm that it is impossible to add new attributes to the parameter class.

    Notes
    -----
    No need to test when creating class (e.g. Param(new_entry=3)) as it will
    not allow input of variables not inputs for __init__.
    However, do need to check it is preventing additions after creating class.
    """
    param = Param()
    with pytest.raises(
        AttributeError, match="only possible to modify existing attributes"
    ):
        param.new_entry = 3


@pytest.mark.parametrize("param_name, value, rule", [
    ("patient_inter", 0, "positive"),
    ("mean_n_consult_time", 0, "positive"),
    ("number_of_runs", 0, "positive"),
    ("audit_interval", 0, "positive"),
    ("number_of_nurses", 0, "positive"),
    ("warm_up_period", -1, "non_negative"),
    ("data_collection_period", -1, "non_negative")
])
def test_negative_inputs(param_name, value, rule):
    """
    Check that the model fails when inputs that are zero or negative are used.

    Parameters
    ----------
    param_name : str
        Name of parameter to change in the Param() class.
    value : float|int
        Invalid value for parameter.
    rule : str
        Either "positive" (if value must be > 0) or "non-negative" (if
        value must be >= 0).
    """
    # Create parameter class with an invalid value
    param = Param(**{param_name: value})

    # Construct the expected error message
    if rule == "positive":
        expected_message = f"Parameter '{param_name}' must be greater than 0."
    else:
        expected_message = (f"Parameter '{param_name}' must be greater than " +
                            "or equal to 0.")

    # Verify that initialising the model raises the correct error
    with pytest.raises(ValueError, match=expected_message):
        Model(param=param, run_number=0)


def test_log_to_console():
    """
    Confirm that logger.log() prints the provided message to the console.
    """
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        logger = SimLogger(log_to_console=True)
        logger.log(sim_time=None, msg="Test console log")
        # Check if console output matches
        assert "Test console log" in mock_stdout.getvalue()


def test_log_to_file():
    """
    Confirm that logger.log() would output the message to a .log file at the
    provided file path.
    """
    # Mock the file open operation
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        # Create the logger and log a simple example
        logger = SimLogger(log_to_file=True, file_path="test.log")
        logger.log(sim_time=None, msg="Log message")
        # Check that the file was opened in write mode at the absolute path
        mock_open.assert_called_with(
            os.path.abspath("test.log"), "w", encoding="locale", errors=None)
        # Verify a FileHandler is attached to the logger
        assert (any(isinstance(handler, logging.FileHandler)
                    for handler in logger.logger.handlers))


def test_invalid_path():
    """
    Ensure there is appropriate error handling for an invalid file path.
    """
    with pytest.raises(ValueError):
        SimLogger(log_to_file=True, file_path="/invalid/path/to/log.log")


def test_invalid_file_extension():
    """
    Ensure there is appropriate error handling for an invalid file extension.
    """
    with pytest.raises(ValueError):
        SimLogger(log_to_file=True, file_path="test.txt")
