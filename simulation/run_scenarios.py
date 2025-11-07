"""
run_scenarios.

Acknowledgements
----------------
This code is adapted from Sammi Rosser and Dan Chalk (2024) HSMA - the
little book of DES (https://github.com/hsma-programme/hsma6_des_book)
(MIT Licence).
"""

import itertools
import pandas as pd

from .param import Param
from .runner import Runner


def run_scenarios(scenarios, param_factory=None, verbose=True):
    """
    Execute a set of scenarios and return the results from each run.

    Parameters
    ----------
    scenarios : dict
        Dictionary where key is name of parameter and value is a list with
        different values to run in scenarios.
    param_factory : callable or None, optional
        A callable that returns a new Param object for each scenario run.
        This can be a class (e.g., `Param`) or a factory function/lambda
        with preset arguments (e.g., `lambda: Param(number_of_runs=4)`).
        If not provided, defaults to using `Param()` with no arguments.
    verbose : bool
        Whether to print messages about scenarios as run.

    Returns
    -------
    pandas.DataFrame
        DataFrame with results from each run of each scenario.

    Notes
    -----
    Function adapted from Rosser, Chalk and Heather 2025.
    """
    # If none provided, use Param
    if param_factory is None:
        param_factory = Param

    # Find every possible permutation of the scenarios
    all_scenarios_tuples = list(itertools.product(*scenarios.values()))

    # Convert back into dictionaries
    all_scenarios_dicts = [
        dict(zip(scenarios.keys(), p)) for p in all_scenarios_tuples
    ]

    # Preview the number of scenarios
    if verbose:
        print(f"There are {len(all_scenarios_dicts)} scenarios. Running:")

    # Run the scenarios...
    results = []
    for index, scenario_to_run in enumerate(all_scenarios_dicts):
        if verbose:
            print(scenario_to_run)

        # Create fresh instance of parameter class for each scenario
        param = param_factory()

        # Update parameter list with the scenario parameters
        param.scenario_name = index
        for key in scenario_to_run:
            setattr(param, key, scenario_to_run[key])
        if verbose:
            print(f"Scenario parameters: {param.__dict__}")

        # Perform replications
        scenario_exp = Runner(param)
        scenario_exp.run_reps()

        # Add scenario number and values to the results dataframe
        for key in scenario_to_run:
            scenario_exp.run_results_df[key] = scenario_to_run[key]

        # Add results from scenario to list
        results.append(scenario_exp.run_results_df)
    return pd.concat(results)
