"""Unit Testing for objects in replications.py

Unit tests are a type of functional testing that focuses on individual
components (e.g. methods, classes) and tests them in isolation to ensure they
work as intended.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:

    pytest
"""

import pytest

from simulation.replications import ReplicationsAlgorithm


# pylint: disable=protected-access
@pytest.mark.parametrize('look_ahead, n, exp', [
    (100, 100, 100),
    (100, 101, 101),
    (0, 500, 0)
])
def test_klimit(look_ahead, n, exp):
    """
    Check that the _klimit() calculations are as expected.

    Arguments:
        look_ahead (int):
            Minimum additional replications to look ahead to assess stability
            of precision.
        n (int):
            Number of replications that would already be completed.
        exp (int):
            Expected number of replications for _klimit() to return.
    """
    # Calculate additional replications that would be required
    calc = ReplicationsAlgorithm(
        look_ahead=100, initial_replications=100)._klimit()
    # Check that this meets our expected value
    assert calc == 100, (
        f'With look_ahead {look_ahead} and n={n}, the additional ' +
        f'replications required should be {exp} but _klimit() returned {calc}.'
    )


@pytest.mark.parametrize('arg, value', [
    ('initial_replications', -1),
    ('initial_replications', 0.5),
    ('look_ahead', -1),
    ('look_ahead', 0.5),
    ('half_width_precision', 0)
])
def test_algorithm_invalid(arg, value):
    """
    Ensure that ReplicationsAlgorithm responds appropriately to invalid inputs.
    """
    with pytest.raises(ValueError):
        ReplicationsAlgorithm(**{arg: value})


def test_algorithm_invalid_budget():
    """
    Ensure that ReplicationsAlgorithm responds appropriately when
    replication_budget is less than initial_replications.
    """
    with pytest.raises(ValueError):
        ReplicationsAlgorithm(initial_replications=10,
                              replication_budget=9)
