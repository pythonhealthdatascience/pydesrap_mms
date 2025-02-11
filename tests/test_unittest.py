"""Unit Testing

Unit tests are a type of functional testing that focuses on individual
components (e.g. methods, classes) and tests them in isolation to ensure they
work as intended.

SimPy itself has lots of tests of the SimPy components themselves, as can view:
https://gitlab.com/team-simpy/simpy/-/tree/master/tests?ref_type=heads.
Hence, our focus here is testing components we have written ourselves.

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

import numpy as np
import pytest

from simulation.logging import SimLogger
from simulation.model import Param, Model, Exponential


def test_new_attribute():
    """
    Confirm that it is impossible to add new attributes to the parameter class.
    """
    # No need to test when creating class (e.g. Param(new_entry=3)) as it will
    # not allow input of variables not inputs for __init__.
    # However, do need to check it is preventing additions after creating class
    param = Param()
    with pytest.raises(AttributeError,
                       match='only possible to modify existing attributes'):
        param.new_entry = 3


@pytest.mark.parametrize('param_name, value, rule', [
    ('patient_inter', 0, 'positive'),
    ('mean_n_consult_time', 0, 'positive'),
    ('number_of_runs', 0, 'positive'),
    ('audit_interval', 0, 'positive'),
    ('number_of_nurses', 0, 'positive'),
    ('warm_up_period', -1, 'non_negative'),
    ('data_collection_period', -1, 'non_negative')
])
def test_negative_inputs(param_name, value, rule):
    """
    Check that the model fails when inputs that are zero or negative are used.

    Arguments:
        param_name (string):
            Name of parameter to change in the Param() class.
        value (float|int):
            Invalid value for parameter.
        rule (string):
            Either 'positive' (if value must be > 0) or 'non-negative' (if
            value must be >= 0).
    """
    # Create parameter class with an invalid value
    param = Param(**{param_name: value})

    # Construct the expected error message
    if rule == 'positive':
        expected_message = f'Parameter "{param_name}" must be greater than 0.'
    else:
        expected_message = (f'Parameter "{param_name}" must be greater than ' +
                            'or equal to 0.')

    # Verify that initialising the model raises the correct error
    with pytest.raises(ValueError, match=expected_message):
        Model(param=param, run_number=0)


def test_exponentional():
    """
    Test that the Exponentional class behaves as expected.
    """
    # Initialise distribution
    d = Exponential(mean=10, random_seed=42)

    # Check that sample is a float
    assert isinstance(d.sample(), float), (
        f'Expected sample() to return a float - instead: {type(d.sample())}'
    )

    # Check that correct number of values are returned
    count = len(d.sample(size=10))
    assert count == 10, (
        f'Expected 10 samples - instead got {count} samples.'
    )

    bigsample = d.sample(size=100000)
    assert all(x > 0 for x in bigsample), (
        'Sample contains non-positive values.'
    )

    # Using the big sample, check that mean is close to expected (allowing
    # some tolerance)
    assert np.isclose(np.mean(bigsample), 10, atol=0.1), (
        'Mean of samples differs beyond tolerance - sample mean ' +
        f'{np.mean(bigsample)}, expected mean 10.'
    )

    # Check that different seeds return different samples
    sample1 = Exponential(mean=10, random_seed=2).sample(size=5)
    sample2 = Exponential(mean=10, random_seed=3).sample(size=5)
    assert not np.array_equal(sample1, sample2), (
        'Samples with different random seeds should not be equal.'
    )


def test_invalid_exponential():
    """
    Ensure that Exponential distribution cannot be created with a negative
    or zero mean.
    """
    # Negative mean
    with pytest.raises(ValueError):
        Exponential(mean=-5, random_seed=42)
    # Zero mean
    with pytest.raises(ValueError):
        Exponential(mean=0, random_seed=42)


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
