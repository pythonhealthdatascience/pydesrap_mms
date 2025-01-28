"""Back testing for the Discrete-Event Simulation (DES) Model.

These check that the model code produces results consistent with prior code.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest

"""

from simulation.model import Defaults, Runner
import pandas as pd
from pathlib import Path


def test_reproduction():
    """
    Check that results from particular run of the model match those previously
    generated using the code.
    """
    # Choose a specific set of parameters
    param = Defaults()
    param.patient_inter = 4
    param.mean_n_consult_time = 10
    param.number_of_nurses = 4
    param.warm_up_period = 500
    param.data_collection_period = 1500
    param.number_of_runs = 5
    param.audit_interval = 50
    param.scenario_name = 0
    param.cores = 1

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
