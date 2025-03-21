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
    ReplicationsAlgorithm)


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
        replications=reps, metrics=['mean_time_with_nurse'])

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
    if not min_reps['mean_time_with_nurse'] <= reps:
        errors.append(
            'The minimum number of replications required as returned by the ' +
            'confidence_interval_method should be less than the number we ' +
            f'ran ({reps}) but it was {min_reps['mean_time_with_nurse']}.')

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
    man_nreps, man_df = ci_function(
        replications=reps, metrics=['mean_time_with_nurse'])

    # Run the algorithm
    analyser = ReplicationsAlgorithm(initial_replications=reps,
                                     look_ahead=0,
                                     replication_budget=reps)
    alg_nreps, alg_df = analyser.select(runner=Runner(Param()),
                                        metrics=['mean_time_with_nurse'])

    # Check that nreps are the same
    assert man_nreps == alg_nreps

    # Get first 20 rows (may have more if met precision and went into
    # look ahead period beyond budget) and compare dataframes
    pd.testing.assert_frame_equal(
        man_df, alg_df.head(20))


def test_algorithm_initial():
    """
    Check that the solution from the ReplicationsAlgorithm is as expected when
    there is a high number of initial replications specified.
    """
    # Set parameters - inc. high number of initial replications & no look-ahead
    # As model is currently designed, all would be solved before 200 reps
    initial_replications = 200
    look_ahead = 0
    metrics = ['mean_time_with_nurse',
               'mean_q_time_nurse',
               'mean_nurse_utilisation']

    # Set up algorithm class
    analyser = ReplicationsAlgorithm(
        initial_replications=initial_replications,
        look_ahead=look_ahead)

    # Run the algorithm
    nreps, summary_table = analyser.select(
        runner=Runner(Param()),
        metrics=metrics)

    # For each metric...
    for metric in metrics:

        # Check that nrow for each metric in summary table equals initial reps
        nrows = len(summary_table[summary_table['metric'] == metric])
        assert nrows == initial_replications

        # Check that all were solved before initial_replications
        assert nreps[metric] < initial_replications


def test_algorithm_nosolution():
    """
    Check that running for less than 3 replications in total will result
    in no solution, and that a warning message is then created.
    """
    # Set up algorithm to run max of 2 replications
    analyser = ReplicationsAlgorithm(
        initial_replications=0, replication_budget=2, look_ahead=0)

    # Run algorithm, checking that it produces a warning
    with pytest.warns(UserWarning):
        solutions, summary_table = analyser.select(
            runner=Runner(Param()), metrics=['mean_time_with_nurse'])

    # Check that there is no solution
    assert solutions['mean_time_with_nurse'] is None

    # Check that the summary tables has no more than 2 rows
    assert len(summary_table) < 3
