"""Functional Testing for objects in replications.py

Functional tests verify that the system or components perform their intended
functionality.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

import pandas as pd
import pytest

from simulation.model import Param, Runner
from simulation.replications import (
    confidence_interval_method, confidence_interval_method_simple,
    ReplicationTabulizer, ReplicationsAlgorithm)


@pytest.mark.parametrize('ci_function', [
    confidence_interval_method,
    confidence_interval_method_simple
])
def test_ci_method_output(ci_function):
    """
    Check that the output from confidence_interval_method and
    confidence_interval_method_simple meets our expectations.

    Arguments:
        ci_function (function):
            Function to run the confidence interval method.
    """
    # Create empty list to store errors (else if each were an assert
    # statement, it would stop after the first)
    errors = []

    # Choose a number of replications to run for
    reps = 20

    # Run the confidence interval method
    min_reps, cumulative_df = ci_function(
        replications=reps, metric='mean_time_with_nurse')

    # Check that the results dataframe contains the right number of rows
    if not len(cumulative_df) == reps:
        errors.append(
            f'Ran {reps} replications but cumulative_df only has ' +
            f'{len(cumulative_df)} entries.')

    # Check that the replications are appropriately numbered
    if not min(cumulative_df['replications']) == 1:
        errors.append(
            'Minimum replication in cumulative_df should be 1 but it is ' +
            f'{min(cumulative_df['replications'])}.')

    if not max(cumulative_df['replications']) == reps:
        errors.append(
            f'As we ran {reps} replications, the maximum replication in ' +
            f'cumulative_df should be {reps} but it is ' +
            f'{max(cumulative_df['replications'])}.')

    # Check that min_reps is no more than the number run
    if not min_reps <= reps:
        errors.append(
            'The minimum number of replications required as returned by the ' +
            'confidence_interval_method should be less than the number we ' +
            f'ran ({reps}) but it returned {min_reps}.')

    # Check if there were any errors
    assert not errors, 'Errors occurred:\n{}'.format('\n'.join(errors))


@pytest.mark.parametrize('ci_function', [
    confidence_interval_method,
    confidence_interval_method_simple
])
def test_consistent_outputs(ci_function):
    """
    Check that the output cumulative statistics from the manual confidence
    interval methods are consistent with those from the algorithm.

    Arguments:
        ci_function (function):
            Function to run the manual confidence interval method.
    """
    # Choose a number of replications to run for
    reps = 20

    # Run the manual confidence interval method
    _, man_df = ci_function(
        replications=reps, metric='mean_time_with_nurse')

    # Run the algorithm
    observer = ReplicationTabulizer()
    analyser = ReplicationsAlgorithm(
        verbose=False,
        observer=observer,
        initial_replications=reps,
        replication_budget=reps)
    _ = analyser.select(runner=Runner(Param()), metric='mean_time_with_nurse')
    # Get first 20 rows (may have more if met precision and went into
    # look ahead period beyond budget)
    auto_df = observer.summary_table().head(20)

    # Compare the dataframes
    pd.testing.assert_frame_equal(man_df, auto_df)
