"""
SimulationAdapter.
"""

from .runner import Runner


class SimulationAdapter:
    """
    Adapter for running model replications compatible with
    ReplicationsAlgorithm.

    Attributes
    ----------
    param : Param
        The simulation parameter object for Runner.
    metrics : list[str]
        The metric(s) to output from each run.
    runner : Runner
        An instance of runner initialised with the provided parameters.
    """
    def __init__(self, param, metrics):
        """
        Initialise adapter.

        Parameters
        ----------
        param : Param
            The simulation parameter object for Runner
        metrics : list[str]
            The metric(s) to output from each run.
        """
        self.param = param
        self.metrics = metrics
        self.runner = Runner(self.param)

    def single_run(self, replication_number):
        """
        Run a single simulation replication and return required metrics.
        """
        result = self.runner.run_single(run=replication_number)
        return {metric: result["run"][metric] for metric in self.metrics}
