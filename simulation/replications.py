"""Selecting the number of replications.

Credit:
    > These functions are adapted from Tom Monks (2021) sim-tools:
    fundamental tools to support the simulation process in python
    (https://github.com/TomMonks/sim-tools) (MIT Licence).
    > In sim-tools, they cite that their implementation is of the "replications
    algorithm" from: Hoad, Robinson, & Davies (2010). Automated selection of
    the number of replications for a discrete-event simulation. Journal of the
    Operational Research Society. https://www.jstor.org/stable/40926090.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.
"""

import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.stats import t
import warnings


class OnlineStatistics:
    """
    """
    def __init__(self, data=None, alpha=0.1, observer=None):
        """
        """
        self.n = 0
        self.x_i = None
        self.mean = None
        self._sq = None
        self.alpha = alpha
        self._observers = []
        if observer is not None:
            self.register_observer(observer)

        if isinstance(data, np.ndarray):
            for x in data:
                self.update(x)

    def register_observer(self, observer):
        """
        """
        self._observers.append(observer)

    @property
    def variance(self):
        """
        """
        return self._sq / (self.n - 1)

    @property
    def std(self):
        """
        """
        if self.n > 2:
            return np.sqrt(self.variance)
        else:
            return np.nan

    @property
    def std_error(self):
        """
        """
        return self.std / np.sqrt(self.n)

    @property
    def half_width(self):
        """
        """
        dof = self.n - 1
        t_value = t.ppf(1 - (self.alpha / 2), dof)
        return t_value * self.std_error

    @property
    def lci(self):
        """
        """
        if self.n > 2:
            return self.mean - self.half_width
        else:
            return np.nan

    @property
    def uci(self):
        """
        Lower confidence interval bound
        """
        if self.n > 2:
            return self.mean + self.half_width
        else:
            return np.nan

    @property
    def deviation(self):
        """
        """
        if self.n > 2:
            return self.half_width / self.mean
        else:
            return np.nan

    def update(self, x):
        """
        """
        self.n += 1
        self.x_i = x

        if self.n == 1:
            self.mean = x
            self._sq = 0
        else:
            updated_mean = self.mean + ((x - self.mean) / self.n)
            self._sq += (x - self.mean) * (x - updated_mean)
            self.mean = updated_mean

        self.notify()

    def notify(self):
        """
        """
        for observer in self._observers:
            observer.update(self)


class ReplicationTabulizer:
    """
    """

    def __init__(self):
        self.stdev = []
        self.lower = []
        self.upper = []
        self.dev = []
        self.cumulative_mean = []
        self.x_i = []
        self.n = 0

    def update(self, results):
        """
        """
        self.x_i.append(results.x_i)
        self.cumulative_mean.append(results.mean)
        self.stdev.append(results.std)
        self.lower.append(results.lci)
        self.upper.append(results.uci)
        self.dev.append(results.deviation)
        self.n += 1

    def summary_table(self):
        """
        """
        results = pd.DataFrame(
            [
                self.x_i,
                self.cumulative_mean,
                self.stdev,
                self.lower,
                self.upper,
                self.dev,
            ]
        ).T
        results.columns = [
            "Mean",
            "Cumulative Mean",
            "Standard Deviation",
            "Lower Interval",
            "Upper Interval",
            "% deviation",
        ]
        results.index = np.arange(1, self.n + 1)
        results.index.name = "replications"

        return results


class ReplicationsAlgorithm:
    """
    """
    def __init__(
        self,
        alpha=0.05,
        half_width_precision=0.05,
        initial_replications=3,
        look_ahead=5,
        replication_budget=1000,
        verbose=False,
        observer=None,
    ):
        """
        """
        self.alpha = alpha
        self.half_width_precision = half_width_precision
        self.initial_replications = initial_replications

        self.look_ahead = look_ahead

        self.replication_budget = replication_budget

        self.verbose = verbose

        self.n = self.initial_replications

        self._n_solution = self.replication_budget

        self.observer = observer

    def _klimit(self) -> int:
        """
        Get the current look ahead. This is lookahead if n<=100, or lookahead
        as a fraction of n if n>100.
        """
        return int((self.look_ahead / 100) * max(self.n, 100))

    def select(self, runner, metric):

        converged = False

        # Run initial replications of the model and get the run results for
        # the specified metric
        x_i = [runner.run_single(rep)['run'][metric]
               for rep in range(self.initial_replications)]

        # Using those results, initialise running mean and std dev
        self.stats = OnlineStatistics(
            data=np.array(x_i), alpha=self.alpha, observer=self.observer
        )

        while not converged and self.n <= self.replication_budget:

            # If after initial replications, update running mean and std dev
            if self.n > self.initial_replications:
                self.stats.update(x_i)

            # If precision has been achieved...
            if self.stats.deviation <= self.half_width_precision:

                # Store current solution
                self._n_solution = self.n
                converged = True

                # If the lookahead period is greater than 0
                if self._klimit() > 0:

                    # Start a new counter
                    k = 1

                    # Whilst the precision is achieved and k is less than
                    # lookahead...
                    while converged and k <= self._klimit():
                        if self.verbose:
                            print(f'{self.n+k}', end=', ')

                        # Run another replication and update the statistics
                        x_i = runner.run_single(run=self.n+k-1)['run'][metric]
                        self.stats.update(x_i)

                        # If precision lost, set converged to false and update
                        # the main counter (n)
                        if self.stats.deviation > self.half_width_precision:
                            converged = False
                            self.n += k
                        # If precision is maintained, update k.
                        else:
                            k += 1

                # If past lookahead and still converged, return _n_solution.
                if converged:
                    return self._n_solution

            # Precision not achieved/maintained, so run another replication
            self.n += 1
            if self.verbose:
                print(f'{self.n}', end=', ')
            x_i = runner.run_single(run=self.n-1)['run'][metric]

        # If not converged and pass replication_budget, end with warning
        warnings.warn(
            f'''Algorithm did not converge for metric '{metric}'. '''
            + 'Returning replication budget as solution'
        )
        return self._n_solution


def confidence_interval_method(
    replications,
    alpha=0.05,
    desired_precision=0.05,
    min_rep=5,
    decimal_places=2,
):
    """
    """
    observer = ReplicationTabulizer()
    stats = OnlineStatistics(
        alpha=alpha, data=replications[:2], observer=observer)

    for i in range(2, len(replications)):
        stats.update(replications[i])

    results = observer.summary_table()

    try:
        n_reps = (
            results.iloc[min_rep:]
            .loc[results["% deviation"] <= desired_precision]
            .iloc[0]
            .name
        )
    except IndexError:
        message = "WARNING: the replications do not reach desired precision"
        warnings.warn(message)
        n_reps = -1

    return n_reps, results.round(decimal_places)


def plotly_confidence_interval_method(
    n_reps, conf_ints, metric_name, figsize=(1200, 400)
):
    """
    """
    fig = go.Figure()

    # Calculate relative deviations [1][4]
    deviation_pct = (
        (conf_ints["Upper Interval"] - conf_ints["Cumulative Mean"])
        / conf_ints["Cumulative Mean"]
        * 100
    ).round(2)

    # Confidence interval bands with hover info
    for col, color, dash in zip(
        ["Lower Interval", "Upper Interval"],
        ["lightblue", "lightblue"], ["dot", "dot"]
    ):
        fig.add_trace(
            go.Scatter(
                x=conf_ints.index,
                y=conf_ints[col],
                line=dict(color=color, dash=dash),
                name=col,
                text=[f"Deviation: {d}%" for d in deviation_pct],
                hoverinfo="x+y+name+text",
            )
        )

    # Cumulative mean line with enhanced hover
    fig.add_trace(
        go.Scatter(
            x=conf_ints.index,
            y=conf_ints["Cumulative Mean"],
            line=dict(color="blue", width=2),
            name="Cumulative Mean",
            hoverinfo="x+y+name",
        )
    )

    # Vertical threshold line
    fig.add_shape(
        type="line",
        x0=n_reps,
        x1=n_reps,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", dash="dash"),
    )

    # Configure layout
    fig.update_layout(
        width=figsize[0],
        height=figsize[1],
        yaxis_title=f"Cumulative Mean: {metric_name}",
        hovermode="x unified",
        showlegend=True,
    )

    return fig