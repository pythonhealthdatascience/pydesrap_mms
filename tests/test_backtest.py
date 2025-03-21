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
from simulation.model import Param, Runner, run_scenarios


def test_reproduction():
    """
    Check that results from particular run of the model match those previously
    generated using the code.
    """
    # Choose a specific set of parameters
    param = Param(
        patient_inter=4,
        mean_n_consult_time=10,
        number_of_nurses=4,
        warm_up_period=500,
        data_collection_period=1500,
        number_of_runs=5,
        audit_interval=50,
        scenario_name=0,
        cores=1
    )

    # Run the replications
    experiment = Runner(param)
    experiment.run_reps()

    # Compare patient-level results
    exp_patient = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/patient.csv'))
    pd.testing.assert_frame_equal(experiment.patient_results_df, exp_patient)

    # Compare run results
    exp_run = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/run.csv'))
    pd.testing.assert_frame_equal(experiment.run_results_df, exp_run)

    # Compare interval audit results
    exp_interval = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/interval.csv'))
    pd.testing.assert_frame_equal(experiment.interval_audit_df, exp_interval)

    # Compare overall results
    exp_overall = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/overall.csv'), index_col=0)
    pd.testing.assert_frame_equal(experiment.overall_results_df, exp_overall)


def test_scenarios():
    """
    Check that results from run with scenarios are consistent with those
    previously generated.
    """
    # Run scenarios
    param = Param(
        patient_inter=4,
        mean_n_consult_time=10,
        number_of_nurses=5,
        warm_up_period=2000,
        data_collection_period=6000,
        number_of_runs=3,
        audit_interval=120,
        cores=1
    )
    results = run_scenarios(
        scenarios={'patient_inter': [3, 4],
                   'number_of_nurses': [6, 7]},
        param=param
    )

    # Compare to expected results
    exp_results = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/scenario.csv'),
        index_col=0)
    pd.testing.assert_frame_equal(results, exp_results)
