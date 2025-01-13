"""Unit testing for the Discrete-Event Simulation (DES) Model.

These check specific parts of the simulation and code, ensuring they work
correctly and as expected.

License:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

# Modify sys.path to include 'scripts' directory
import os
import sys
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'scripts')))

# Import other modules
from scripts.simulation.model import Defaults, Exponential, Model, Trial
import numpy as np
import pandas as pd
import pytest


def test_new_attribute():
    """
    Confirm that it is not possible to add new attributes to Defaults.
    """
    param = Defaults()
    with pytest.raises(AttributeError,
                       match='only possible to modify existing attributes'):
        param.new_entry = 3


@pytest.mark.parametrize('param_name, value, rule', [
    ('patient_inter', 0, 'positive'),
    ('mean_n_consult_time', 0, 'positive'),
    ('number_of_runs', 0, 'positive'),
    ('audit_interval', 0, 'positive'),
    ('warm_up_period', -1, 'non_negative'),
    ('data_collection_period', -1, 'non_negative')
])
def test_negative_inputs(param_name, value, rule):
    """
    Check that the model fails when inputs that are zero or negative are used.

    Arguments:
        param_name (string):
            Name of parameter to change from the Defaults() class.
        value (float|int):
            Invalid value for parameter.
        rule (string):
            Either 'positive' (if value must be > 0) or 'non-negative' (if
            value must be >= 0).
    """
    param = Defaults()

    # Set parameter to an invalid value
    setattr(param, param_name, value)

    # Construct the expected error message
    if rule == 'positive':
        expected_message = f'Parameter "{param_name}" must be greater than 0.'
    elif rule == 'non_negative':
        expected_message = (f'Parameter "{param_name}" must be greater than ' +
                            'or equal to 0.')

    # Verify that initialising the model raises the correct error
    with pytest.raises(ValueError, match=expected_message):
        Model(param=param, run_number=0)


def test_negative_results():
    """
    Check that values are non-negative.
    """
    # Run model with standard parameters
    model = Model(param=Defaults(), run_number=0)
    model.run()

    # Check that at least one patient was processed
    error_msg = ('Model should process at least one patient, but processed: ' +
                 f'{len(model.results_list)}.')
    assert len(model.results_list) > 0, error_msg

    # Check that queue time is non-negative
    for result in model.results_list:
        error_msg = ('Nurse queue time should not be negative, but found: ' +
                     f'{result['q_time_nurse']}.')
        assert result['q_time_nurse'] >= 0, error_msg

    # Check that consultation time is non-negative
    for result in model.results_list:
        error_msg = ('Nurse consultation times should not be negative, but ' +
                     f'found: {result['time_with_nurse']}.')
        assert result['time_with_nurse'] >= 0, error_msg


def test_high_demand():
    """
    Test utilisation remains between 0 and 1 under an extreme case, and that
    unseen patients are still in the dataset.
    """
    # Run model with high number of arrivals and only one nurse
    param = Defaults()
    param.number_of_nurses = 1
    param.patient_inter = 0.1
    trial = Trial(param)
    results = trial.run_single(run=0)

    # Check that the utilisation as calculated from total_nurse_time_used
    # does not exceed 1 or drop below 0
    util = results['trial']['mean_nurse_utilisation']
    assert util <= 1, (
        'The trial `mean_nurse_utilisation` should not exceed 1, but ' +
        f'found utilisation of {util}.'
    )
    assert util >= 0, (
        'The trial `mean_nurse_utilisation` should not drop below 0, but ' +
        f'found utilisation of {util}.'
    )

    # Check that the utilisation recorded by the interval audit does not
    # exceed 1 or drop below 0
    util_high = [x <= 1 for x in results['interval_audit']['utilisation']]
    util_low = [x >= 0 for x in results['interval_audit']['utilisation']]
    assert all(util_high), (
        'The interval audit must not record any utilisation that exceeds 1.'
    )
    assert all(util_low), (
        'The interval audit must not record any utilisation that is below 0.'
    )

    # Check that the final patient in the patient-level results is not seen
    # by a nurse.
    last_patient = results['patient'].iloc[-1]
    assert np.isnan(last_patient['q_time_nurse']), (
        'Expect last patient in high demand scenario to have queue time NaN.'
    )
    assert np.isnan(last_patient['time_with_nurse']), (
        'Expect last patient in high demand scenario to have NaN for time' +
        'with nurse.'
    )


def test_warmup_only():
    """
    Ensures no results are recorded during the warm-up phase.

    This is tested by running the simulation model with only a warm-up period,
    and then checking that results are all zero or empty.
    """
    # Run model with only a warm-up period and no time for results collection.
    param = Defaults()
    param.warm_up_period = 500
    param.data_collection_period = 0
    model = Model(param, run_number=0)
    model.run()

    # Check that time spent with nurse is 0
    error_msg = ('Nurse time should equal zero, but found: ' +
                 f'{model.nurse_time_used}')
    assert model.nurse_time_used == 0, error_msg

    # Check that there are no patient results recorded
    error_msg = ('Patient result list should be empty, but found ' +
                 f'{len(model.results_list)} entries.')
    assert len(model.results_list) == 0, error_msg

    # Check that there are no records in interval audit
    error_msg = ('Interval audit list should be empty, but found ' +
                 f'{len(model.audit_list)} entries.')
    assert len(model.audit_list) == 0, error_msg


def test_warmup_impact():
    """
    Check that running with warm-up leads to different results than without.
    """
    def helper_warmup(warm_up_period):
        """
        Helper function to run model with high arrivals and specified warm-up.

        Arguments:
            warm_up_period (float):
                Duration of the warm-up period - running simulation but not yet
                collecting results.
        """
        param = Defaults()
        param.patient_inter = 1
        param.warm_up_period = warm_up_period
        param.data_collection_period = 1500
        trial = Trial(param)
        return trial.run_single(run=0)

    # Run model with and without warm-up period
    results_warmup = helper_warmup(warm_up_period=500)
    results_none = helper_warmup(warm_up_period=0)

    # Extract result of first patient
    first_warmup = results_warmup['patient'].iloc[0]
    first_none = results_none['patient'].iloc[0]

    # Check that model with warm-up has arrival time later than warm-up length
    # and queue time greater than 0
    assert first_warmup['arrival_time'] > 500, (
        'Expect first patient to arrive after time 500 when model is run ' +
        f'with warm-up, but got {first_warmup["arrival_time"]}.'
    )
    assert first_warmup['q_time_nurse'] > 0, (
        'Expect first patient to need to queue in model with warm-up and ' +
        f'high arrival rate, but got {first_warmup['q_time_nurse']}.'
    )

    # Check that model without warm-up has arrival and queue time of 0
    assert first_none['arrival_time'] == 0, (
        'Expect first patient to arrive at time 0 when model is run ' +
        f'without warm-up, but got {first_none['arrival_time']}.'
    )
    assert first_none['q_time_nurse'] == 0, (
        'Expect first patient to have no wait time in model without warm-up ' +
        f'but got {first_none['q_time_nurse']}.'
    )


def test_arrivals():
    """
    Check that trial-level count of arrivals is consistent with the number of
    patients recorded in the patient-level results.
    """
    trial = Trial(Defaults())
    trial.run_trial()

    # Get count of patients from patient-level and trial-level results
    patient_n = trial.patient_results_df.groupby('run')['patient_id'].count()
    trial_n = trial.trial_results_df['arrivals']

    # Compare the counts from each run
    assert all(patient_n == trial_n), (
        'The number of arrivals in the trial-level results should be ' +
        'consistent with the number of patients in the patient-level results.'
    )


@pytest.mark.parametrize('param_name, initial_value, adjusted_value', [
    ('number_of_nurses', 3, 9),
    ('patient_inter', 2, 15),
    ('mean_n_consult_time', 30, 3),
])
def test_waiting_time_utilisation(param_name, initial_value, adjusted_value):
    """
    Test that adjusting parameters decreases the waiting time and utilisation.

    Arguments:
        param_name (string):
            Name of parameter to change from the Defaults() class.
        initial_value (float|int):
            Value with which we expect longer waiting times.
        adjusted_value (float|int):
            Value with which we expect shorter waiting time.
    """
    # Define helper function for the test
    def helper_param(param_name, value):
        """
        Helper function to set a specific parameter value, run the model,
        and return the waiting time.

        Arguments:
            param_name (string):
                Name of the parameter to modify.
            value (float|int):
                Value to assign to the parameter.

        Returns:
            float:
                Mean queue time for nurses.
        """
        # Create a default parameter, but set some specific values
        # (which will ensure sufficient arrivals/capacity/etc. that we will
        # see variation in wait time, and not just no wait time with all
        # different parameters tried).
        param = Defaults()
        param.number_of_nurses = 4
        param.patient_inter = 3
        param.mean_n_consult_time = 15

        # Modify chosen parameter for the test
        setattr(param, param_name, value)

        # Run the trial and return the mean queue time for nurses
        trial = Trial(param)
        return trial.run_single(run=0)['trial']

    # Run model with initial and adjusted values
    initial_results = helper_param(param_name, initial_value)
    adjusted_results = helper_param(param_name, adjusted_value)

    # Check that waiting times from adjusted model are lower
    initial_wait = initial_results['mean_q_time_nurse']
    adjusted_wait = adjusted_results['mean_q_time_nurse']
    assert initial_wait > adjusted_wait, (
        f'Changing "{param_name}" from {initial_value} to {adjusted_value} ' +
        'did not decrease waiting time as expected: observed waiting times ' +
        f'of {initial_wait} and {adjusted_wait}, respectively.'
    )

    # Check that utilisation from adjusted model is lower
    initial_util = initial_results['mean_nurse_utilisation']
    adjusted_util = adjusted_results['mean_nurse_utilisation']
    assert initial_util > adjusted_util, (
        f'Changing "{param_name}" from {initial_value} to {adjusted_value} ' +
        'did not increase utilisation as expected: observed utilisation ' +
        f'of {initial_util} and {adjusted_util}, respectively.'
    )


@pytest.mark.parametrize('param_name, initial_value, adjusted_value', [
    ('patient_inter', 2, 15),
    ('data_collection_period', 2000, 500)
])
def test_arrivals_decrease(param_name, initial_value, adjusted_value):
    """
    Test that adjusting parameters reduces the number of arrivals as expected.
    """
    # Run model with initial value
    param = Defaults()
    setattr(param, param_name, initial_value)
    trial = Trial(param)
    initial_arrivals = trial.run_single(run=0)['trial']['arrivals']

    # Run model with adjusted value
    param = Defaults()
    setattr(param, param_name, adjusted_value)
    trial = Trial(param)
    adjusted_arrivals = trial.run_single(run=0)['trial']['arrivals']

    # Check that arrivals from adjusted model are less
    assert initial_arrivals > adjusted_arrivals, (
        f'Changing "{param_name}" from {initial_value} to {adjusted_value} ' +
        'did not decrease the number of arrivals as expected: observed ' +
        f'{initial_arrivals} and {adjusted_arrivals} arrivals, respectively.'
    )


def test_seed_stability():
    """
    Check that two runs using the same random seed return the same results.
    """
    # Run trial twice, with same run number (and therefore same seed) each time
    trial1 = Trial(param=Defaults())
    result1 = trial1.run_single(run=33)
    trial2 = Trial(param=Defaults())
    result2 = trial2.run_single(run=33)

    # Check that dataframes with patient-level results are equal
    pd.testing.assert_frame_equal(result1['patient'], result2['patient'])


def test_interval_audit_time():
    """
    Check that length of interval audit is less than the length of simulation.
    """
    # Run single trial with default parameters and get max time from audit
    param = Defaults()
    trial = Trial(param)
    results = trial.run_single(run=0)
    max_time = max(results['interval_audit']['simulation_time'])

    # Check that max time in audit is less than simulation length
    full_simulation = param.warm_up_period + param.data_collection_period
    assert max_time < full_simulation, (
        f'Max time in interval audit ({max_time}) is greater than length ' +
        f'of the simulation ({full_simulation}).'
    )


def test_exponentional():
    """
    Test that the Exponentional class behaves as expected.
    """
    # Initialise distribution
    d = Exponential(mean=10, random_seed=42)

    # Check that sample is a float
    assert type(d.sample()) == float, (
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


def test_parallel():
    """
    Check that sequential and parallel execution produce consistent results.
    """
    # Sequential (1 core) and parallel (-1 cores) execution
    results = {}
    for mode, cores in [('seq', 1), ('par', -1)]:
        param = Defaults()
        param.cores = cores
        trial = Trial(param)
        results[mode] = trial.run_single(run=0)

    # Verify results are identical
    pd.testing.assert_frame_equal(
        results['seq']['patient'], results['par']['patient'])
    pd.testing.assert_frame_equal(
        results['seq']['interval_audit'], results['par']['interval_audit'])
    assert results['seq']['trial'] == results['par']['trial']
