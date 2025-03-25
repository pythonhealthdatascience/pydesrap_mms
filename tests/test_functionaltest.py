"""Functional Testing

Functional tests verify that the system or components perform their intended
functionality.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

from joblib import cpu_count
import numpy as np
import pandas as pd
import pytest
import simpy
from simulation.model import Param, Model, Runner, MonitoredResource


def test_negative_results():
    """
    Check that values are non-negative.
    """
    # Run model with standard parameters
    model = Model(param=Param(), run_number=0)
    model.run()

    # Check that at least one patient was processed
    error_msg = ('Model should process at least one patient, but processed: ' +
                 f'{len(model.results_list)}.')
    assert len(model.results_list) > 0, error_msg

    # Check that queue time is non-negative
    for result in model.results_list:
        error_msg = ('Nurse queue time should not be negative, but found: ' +
                     f'{result["q_time_nurse"]}.')
        assert result['q_time_nurse'] >= 0, error_msg

    # Check that consultation time is non-negative
    for result in model.results_list:
        error_msg = ('Nurse consultation times should not be negative, but ' +
                     f'found: {result["time_with_nurse"]}.')
        assert result['time_with_nurse'] >= 0, error_msg


def test_high_demand():
    """
    Test utilisation remains between 0 and 1 under an extreme case, and that
    unseen patients are still in the dataset.
    """
    # Run model with high number of arrivals and only one nurse
    param = Param(number_of_nurses=1,
                  patient_inter=0.1)
    experiment = Runner(param)
    results = experiment.run_single(run=0)

    # Check that the utilisation as calculated from total_nurse_time_used
    # does not exceed 1 or drop below 0
    util = results['run']['mean_nurse_utilisation']
    assert util == pytest.approx(1, abs=1e-9) or util < 1, (
        'The run `mean_nurse_utilisation` should not exceed 1, but ' +
        f'found utilisation of {util}.'
    )
    assert util >= 0, (
        'The run `mean_nurse_utilisation` should not drop below 0, but ' +
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


def test_warmup_high_demand():
    """
    Test that utilisation is 1 due to high demand from warm-up (WU), even if
    none of that resource usage actually reflects use by patients from the data
    collection (DC) period.
    """
    param = Param(number_of_nurses=1,
                  patient_inter=0.1,
                  warm_up_period=100,
                  data_collection_period=10)
    experiment = Runner(param)
    results = experiment.run_single(run=0)

    # ONLY REFLECTS DC PATIENTS
    # Expect these to be NaN, as no patients in data collection period seen,
    # and we're not interested in the wait times of the warm-up patients
    assert np.isnan(results['run']['mean_q_time_nurse'])
    assert np.isnan(results['run']['mean_time_with_nurse'])

    # REFLECTS USE BY WU + DC PATIENTS
    # Expect these to be 1, as nurses busy for whole time
    assert results['run']['mean_nurse_utilisation'] == 1
    assert results['run']['mean_nurse_utilisation_tw'] == 1
    assert results['interval_audit']['utilisation'][0] == 1

    # REFLECTS USE BY WU + DC PATIENTS
    # Expect this to be positive and greater than arrivals
    assert results['run']['mean_nurse_q_length'] > results['run']['arrivals']

    # ONLY REFLECTS DC PATIENTS
    # Expect this to match arrivals
    assert results['run']['count_nurse_unseen'] == results['run']['arrivals']

    # ONLY REFLECTS DC PATIENTS
    # Expect this to be positive and close to 5 (as mean of arrivals in 10 min)
    assert results['run']['mean_q_time_nurse_unseen'] > 0
    assert pytest.approx(results['run']['mean_q_time_nurse_unseen'], 0.1) == 5


def test_warmup_only():
    """
    Ensures no results are recorded during the warm-up phase.

    This is tested by running the simulation model with only a warm-up period,
    and then checking that results are all zero or empty.
    """
    # Run model with only a warm-up period and no time for results collection.
    param = Param(warm_up_period=500,
                  data_collection_period=0)
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
        param = Param(patient_inter=1,
                      warm_up_period=warm_up_period,
                      data_collection_period=1500)
        experiment = Runner(param)
        return experiment.run_single(run=0)

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
        f'with warm-up (length 500), but got {first_warmup["arrival_time"]}.'
    )
    assert first_warmup['q_time_nurse'] > 0, (
        'Expect first patient to need to queue in model with warm-up and ' +
        f'high arrival rate, but got {first_warmup["q_time_nurse"]}.'
    )

    # Check that model without warm-up has arrival first arrival after time 0,
    # but a queue time of 0
    assert first_none['arrival_time'] > 0, (
        'Expect first patient to arrive after time 0 when model is run ' +
        f'without warm-up, but got {first_none["arrival_time"]}.'
    )
    assert first_none['q_time_nurse'] == 0, (
        'Expect first patient to have no wait time in model without warm-up ' +
        f'but got {first_none["q_time_nurse"]}.'
    )

    # Check that the first interval audit entry with no warm-up has time and
    # no queue or wait time. However, as our first patient arrives at time 0,
    # we do expect to have utilisation over 0.
    first_interval = results_none['interval_audit'].iloc[0]
    assert first_interval['simulation_time'] == 0, (
        'With no warm-up, expect first entry in interval audit to be ' +
        f'at time 0, but it was at time {first_interval['simulation_time']}.'
    )
    assert first_interval['utilisation'] == 0, (
        'With no warm-up, expect first entry in interval audit to ' +
        'have utilisation of 0 but utilisation was ' +
        f'{first_interval['utilisation']}.'
    )
    assert first_interval['queue_length'] == 0, (
        'With no warm-up, expect first entry in interval audit to ' +
        'have no queue, but there was queue length of ' +
        f'{first_interval['queue_length']}.'
    )
    assert first_interval['running_mean_wait_time'] == 0, (
        'With no warm-up, expect first entry in interval audit to ' +
        'have running mean wait time of 0 but it was ' +
        f'{first_interval['running_mean_wait_time']}.'
    )

    # Check that first interval audit entry with a warm-up has time 500
    # (matching length of warm-up period) - and so ensuring the first entry
    # in the interval audit, which occurs at the end of the warm-up period,
    # has not been deleted.
    first_interval_warmup = results_warmup['interval_audit'].iloc[0]
    assert first_interval_warmup['simulation_time'] == 500, (
        'With warm-up of 500, expect first entry in interval audit to be ' +
        f'at time 500, but it was at time {first_interval['simulation_time']}.'
    )


def test_arrivals():
    """
    Check that count of arrivals in each run is consistent with the number of
    patients recorded in the patient-level results.
    """
    experiment = Runner(Param())
    experiment.run_reps()

    # Get count of patients from patient-level and run results
    patient_n = (experiment
                 .patient_results_df
                 .groupby('run')['patient_id']
                 .count())
    run_n = experiment.run_results_df['arrivals']

    # Compare the counts from each run
    assert all(patient_n == run_n), (
        'The number of arrivals in the results from each run should be ' +
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
            Name of parameter to change in the Param() class.
        initial_value (float|int):
            Value with which we expect longer waiting times.
        adjusted_value (float|int):
            Value with which we expect shorter waiting time.
    """
    # Define helper function for the test
    def helper_param(param_name, value):
        """
        Helper function to set a specific parameter value, run the model,
        and return the results from a single run.

        Arguments:
            param_name (string):
                Name of the parameter to modify.
            value (float|int):
                Value to assign to the parameter.

        Returns:
            dict:
                'run' dictionary from the run_single() output, containing the
                average results from run/s of the model.
        """
        # Create a default parameter, but set some specific values
        # (which will ensure sufficient arrivals/capacity/etc. that we will
        # see variation in wait time, and not just no wait time with all
        # different parameters tried, or no patients seen as waiting for
        # backlog from warm-up), then modify chosen parameter for test.
        param = Param(number_of_nurses=4,
                      patient_inter=3,
                      mean_n_consult_time=15,
                      warm_up_period=1440*10)
        setattr(param, param_name, value)

        # Run a single replication and return the results for that run
        experiment = Runner(param)
        return experiment.run_single(run=0)['run']

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
    param = Param(**{param_name: initial_value})
    experiment = Runner(param)
    initial_arrivals = experiment.run_single(run=0)['run']['arrivals']

    # Run model with adjusted value
    param = Param(**{param_name: adjusted_value})
    experiment = Runner(param)
    adjusted_arrivals = experiment.run_single(run=0)['run']['arrivals']

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
    # Run model twice, with same run number (and therefore same seed) each time
    experiment1 = Runner(param=Param())
    result1 = experiment1.run_single(run=33)
    experiment2 = Runner(param=Param())
    result2 = experiment2.run_single(run=33)

    # Check that dataframes with patient-level results are equal
    pd.testing.assert_frame_equal(result1['patient'], result2['patient'])


def test_interval_audit_time():
    """
    Check that length of interval audit is less than the length of simulation.
    """
    # Run model once with default parameters and get max time from audit
    param = Param()
    experiment = Runner(param)
    results = experiment.run_single(run=0)
    max_time = max(results['interval_audit']['simulation_time'])

    # Check that max time in audit is less than simulation length
    full_simulation = param.warm_up_period + param.data_collection_period
    assert max_time < full_simulation, (
        f'Max time in interval audit ({max_time}) is greater than length ' +
        f'of the simulation ({full_simulation}).'
    )


def test_parallel():
    """
    Check that sequential and parallel execution produce consistent results.
    """
    # Sequential (1 core) and parallel (-1 cores) execution
    results = {}
    for mode, cores in [('seq', 1), ('par', -1)]:
        param = Param(cores=cores)
        experiment = Runner(param)
        results[mode] = experiment.run_single(run=0)

    # Verify results are identical
    pd.testing.assert_frame_equal(
        results['seq']['patient'], results['par']['patient'])
    pd.testing.assert_frame_equal(
        results['seq']['interval_audit'], results['par']['interval_audit'])
    assert results['seq']['run'] == results['par']['run']


@pytest.mark.parametrize('cores', [
    (-2), (0), (cpu_count()), (cpu_count()+1)
])
def test_valid_cores(cores):
    """
    Check there is error handling for input of invalid number of cores.
    """
    param = Param(cores=cores)
    runner = Runner(param)
    with pytest.raises(ValueError):
        runner.run_reps()


def test_consistent_metrics():
    """
    Expect utilisation to be pretty much the same, between the two methods
    implemented for calculating the overall mean utilisation.
    """
    # Run default model
    experiment = Runner(Param())
    experiment.run_reps()

    # Check nurse utilisation
    pd.testing.assert_series_equal(
        experiment.run_results_df['mean_nurse_utilisation'],
        experiment.run_results_df['mean_nurse_utilisation_tw'],
        atol=0.001,
        check_names=False)


def test_monitoredresource_cleanup():
    """
    Run simple example and check that the monitored resource calculations
    are as expected (e.g. clean-up was performed appropriately at end of
    simulation).
    """
    # Simulation setup
    env = simpy.Environment()
    resource = MonitoredResource(env, capacity=1)

    def process_task(env, resource, duration):
        """Simulate a task that requests the resource."""
        with resource.request() as req:
            yield req
            yield env.timeout(duration)

    # Set run length
    run_length = 12

    # Schedule tasks to occur during the simulation
    env.process(process_task(env, resource, duration=5))  # Task A
    env.process(process_task(env, resource, duration=10))  # Task B
    env.process(process_task(env, resource, duration=15))  # Task C

    # Run the simulation
    env.run(until=run_length)

    # If the simulation ends while resources are still in use or requests are
    # still in the queue, the time between the last recorded event and the
    # simulation end will not have been accounted for. Hence, we call
    # update_time_weighted_stats() to run for time between last event and end.
    resource.update_time_weighted_stats()

    # Assertions
    # At time=12:
    # - Task A is done (0-5)
    # - Task B is still using the resource (5-15)
    # - Task C is still waiting in the queue (15-30)
    # Hence...

    # Expected queue time: 17, as task B (5) + task C (12)
    expected_queue_time = 17.0

    # Expected busy time: 12, as one resource busy for the whole simulation
    expected_busy_time = 12.0

    # Run assertions
    assert sum(resource.area_n_in_queue) == expected_queue_time, (
        f'Expected queue time {expected_queue_time} but ' +
        f'observed {resource.area_n_in_queue}.'
    )
    assert sum(resource.area_resource_busy) == expected_busy_time, (
        f'Expected queue time {expected_busy_time} but ' +
        f'observed {resource.area_resource_busy}.'
    )


def test_extreme_interarrival():
    """
    Check that extremely high interarrival time results in no arrivals, and
    that the model can cope with having no arrivals.
    """
    param = Param(patient_inter=99999999,
                  warm_up_period=0,
                  data_collection_period=10000)
    experiment = Runner(param)
    results = experiment.run_single(run=0)

    assert results['run']['arrivals'] < 1, (
        'Expect no arrivals due to extreme interarrival time.'
    )


def test_extreme_nurses():
    """
    Check that extremely high number of nurses results in no wait times and all
    patients being seen.
    """
    # Run model with extremely large number of nurses
    param = Param(number_of_nurses=10_000_000)
    experiment = Runner(param)
    results = experiment.run_single(run=0)

    # Check that no patients wait
    assert results['run']['mean_q_time_nurse'] == 0, (
        'Expect no patients to wait but mean wait time is ' +
        f'{results['run']['mean_q_time_nurse']:.2f}.'
    )

    # Check that all patients are seen
    assert results['run']['count_nurse_unseen'] == 0, (
        'Expect all patients to be seen, but ' +
        f'{results['run']['count_nurse_unseen']} were not seen by a nurse.'
    )
    assert np.isnan(results['run']['mean_q_time_nurse_unseen']), (
        'Expect all patients to be seen, and so have no mean wait time for ' +
        'unseen patients, but was ' +
        f'{results['run']['mean_q_time_nurse_unseen']:.2f}.'
    )


def test_no_missing_values():
    """
    Some columns are expected to have some NaN - but for those that don't,
    check that no missing values exist in the final output.
    """
    param = Param()
    experiment = Runner(param)
    experiment.run_reps()

    # Define required columns we expect to have no missing values
    req_patient = ['patient_id', 'arrival_time', 'run']
    req_run = ['run_number', 'scenario', 'arrivals', 'mean_q_time_nurse',
               'mean_time_with_nurse', 'mean_nurse_utilisation',
               'mean_nurse_utilisation_tw', 'mean_nurse_q_length',
               'count_nurse_unseen']

    # Check for missing values
    res_patient = experiment.patient_results_df[req_patient].isnull().any()
    assert not res_patient.any(), {
        'Found missing values in patient results in columns that we expect ' +
        f'to have none - in the columns marked True: {res_patient}'
    }
    res_run = experiment.run_results_df[req_run].isnull().any()
    assert not res_run.any(), {
        'Found missing values in run results in columns that we expect ' +
        f'to have none - in the columns marked True: {res_run}'
    }
    res_interval = experiment.interval_audit_df.isnull().any()
    assert not res_interval.any(), {
        'Found missing values in interval results - in the columns marked ' +
        f'True: {res_interval}'
    }
    res_overall = experiment.overall_results_df.isnull().any()
    assert not res_overall.any(), {
        'Found missing values in overall results - in the columns marked ' +
        f'True: {res_overall}'
    }


def test_sampled_times():
    """
    Ensure that the mean of inter-arrival and consultation times are close to
    expected value.
    """
    param = Param(patient_inter=5, mean_n_consult_time=8)
    experiment = Runner(param)
    results = experiment.run_single(run=0)

    # Calculate the inter-arrival times between patients (from arrival times)
    actual_interarrival = np.diff(sorted(results['patient']['arrival_time']))

    # Check that the mean inter-arrival time is close to 5
    observed_mean_iat = np.mean(actual_interarrival)
    assert np.isclose(observed_mean_iat, 5, atol=0.5), (
        f'Expected mean interarrival time ≈ 5, but got {observed_mean_iat}.'
    )

    # Check that the mean nurse consultation time is close to 8
    observed_mean_nur = results['patient']['time_with_nurse'].mean()
    assert np.isclose(observed_mean_nur, 8, atol=0.5), (
        f"Expected mean consultation time ≈ 8, but got {observed_mean_nur}."
    )
