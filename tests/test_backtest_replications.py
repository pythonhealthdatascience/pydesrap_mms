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
    ReplicationTabulizer, ReplicationsAlgorithm)


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
    # Run the confidence interval method
    _, cumulative_df = ci_function(
        replications=20, metric='mean_time_with_nurse')

    # Import the expected results
    exp_df = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/replications.csv'))

    # Compare them
    pd.testing.assert_frame_equal(cumulative_df, exp_df)


def test_algorithm():
    """
    Check that the ReplicationsAlgorithm produces results consistent with those
    previously generated.
    """
    # Run the algorithm
    observer = ReplicationTabulizer()
    analyser = ReplicationsAlgorithm(
        verbose=False,
        observer=observer,
        initial_replications=20,
        replication_budget=20)
    _ = analyser.select(runner=Runner(Param()), metric='mean_time_with_nurse')
    # Get first 20 rows (may have more if met precision and went into
    # look ahead period beyond budget)
    cumulative_df = observer.summary_table().head(20)

    # Import the expected results
    exp_df = pd.read_csv(
        Path(__file__).parent.joinpath('exp_results/replications.csv'))

    # Compare them
    pd.testing.assert_frame_equal(cumulative_df, exp_df)
