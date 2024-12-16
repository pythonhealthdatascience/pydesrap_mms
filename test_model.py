from model import Defaults, Model, Trial
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
        Model(param)


def test_negative_results():
    """
    Check that values are non-negative.
    """
    # Run model with standard parameters
    model = Model(param=Defaults())
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


def test_warmup():
    """
    Ensures no results are recorded during the warm-up phase.

    This is tested by running the simulation model with only a warm-up period,
    and then checking that results are all zero or empty.
    """
    # Run model with only a warm-up period and no time for results collection.
    param = Defaults()
    param.warm_up_period = 500
    param.data_collection_period = 0
    model = Model(param)
    model.run()

    # Check that time spent with nurse is 0
    error_msg = ('Nurse time should equal zero, but found: ' +
                 f'{model.nurse_time_used}')
    assert model.nurse_time_used == 0, error_msg

    # Check that there are no patient results recorded
    error_msg = ('Patient result list should be empty, but found ' +
                 f'{len(model.results_list)} entries.')
    assert len(model.results_list) == 0, error_msg

    # Check that there are no records of utilisation
    error_msg = ('Utilisation audit list should be empty, but found ' +
                 f'{len(model.utilisation_audit)} entries.')
    assert len(model.utilisation_audit) == 0, error_msg


@pytest.mark.parametrize('param_name, initial_value, adjusted_value', [
    ('number_of_nurses', 1, 9),
    ('patient_inter', 2, 15),
    ('mean_n_consult_time', 30, 3),
])
def test_waiting_time_decrease(param_name, initial_value, adjusted_value):
    """
    Test that adjusting parameters decreases the waiting time as expected.

    Arguments:
        param_name (string):
            Name of parameter to change from the Defaults() class.
        initial_value (float|int):
            Value with which we expect longer waiting times.
        adjusted_value (float|int):
            Value with which we expect shorter waiting times.
    """
    # Define helper function for the test
    def run_model_with_param(param_name, value):
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
        return trial.run_single(run=0)['trial']['mean_q_time_nurse']

    # Run model with initial and adjusted values
    initial_wait = run_model_with_param(param_name, initial_value)
    adjusted_wait = run_model_with_param(param_name, adjusted_value)

    # Check that waiting times from adjusted model are lower
    assert initial_wait > adjusted_wait, (
        f'Reducing "{param_name}" from {initial_value} to {adjusted_value} ' +
        'did not decrease waiting time as expected: observed waiting times ' +
        f'of {initial_wait} and {adjusted_wait}, respectively.'
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
