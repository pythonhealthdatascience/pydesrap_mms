from model import Model, Defaults
import pytest


def test_negative_results():
    """
    Check that values are non-negative.
    """
    # Run model with standard parameters
    model = Model()
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
