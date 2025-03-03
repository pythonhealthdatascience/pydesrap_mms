"""Back Testing

Back tests check that the model code produces results consistent with those
generated historically/from prior code.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

from pathlib import Path

import pandas as pd
import pytest

from simulation.model import Runner, Param
from simulation.replications import (
    confidence_interval_method, confidence_interval_method_simple,
    ReplicationsAlgorithm)


@pytest.mark.parametrize('ci_function', [
    confidence_interval_method,
    confidence_interval_method_simple
])
def test_cimethods(ci_function):
    """
    Check that results from the manual confidence interval methods are
    consistent with those generated previously.

    Arguments:
        ci_function (function):
            Function to run the manual confidence interval method.
    """
    # Specify the parameters for this back test (so remains consistent even if
    # defaults used are changed)
    param = Param(
        patient_inter=4,
        mean_n_consult_time=10,
        number_of_nurses=5,
        warm_up_period=1440*13,
        data_collection_period=1440*30,
        number_of_runs=31,
        audit_interval=120,
        scenario_name=0,
        cores=1
    )

    # Run the confidence interval method
    _, cumulative_df = ci_function(
        replications=40,
        metrics=['mean_time_with_nurse',
                 'mean_q_time_nurse',
                 'mean_nurse_utilisation'],
        param=param)

    # Import the expected results
    exp_df = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/replications.csv'))

    # Compare them
    pd.testing.assert_frame_equal(cumulative_df.reset_index(drop=True),
                                  exp_df.reset_index(drop=True))


def test_algorithm():
    """
    Check that the ReplicationsAlgorithm produces results consistent with those
    previously generated.
    """
    # Specify the parameters for this back test (so remains consistent even if
    # defaults used are changed)
    param = Param(
        patient_inter=4,
        mean_n_consult_time=10,
        number_of_nurses=5,
        warm_up_period=1440*13,
        data_collection_period=1440*30,
        number_of_runs=31,
        audit_interval=120,
        scenario_name=0,
        cores=1
    )

    # Run the algorithm, forcing only 40 replications
    analyser = ReplicationsAlgorithm(initial_replications=40,
                                     replication_budget=40,
                                     look_ahead=0)
    _, summary_table = analyser.select(
        runner=Runner(param), metrics=['mean_time_with_nurse',
                                       'mean_q_time_nurse',
                                       'mean_nurse_utilisation'])

    # Import the expected results
    exp_df = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/replications.csv'))

    # Compare dataframes
    pd.testing.assert_frame_equal(summary_table.reset_index(drop=True),
                                  exp_df.reset_index(drop=True))
