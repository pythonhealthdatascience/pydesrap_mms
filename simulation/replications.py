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

import warnings

import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.stats import t

from simulation.model import Param, Runner
from simulation.helper import summary_stats


class OnlineStatistics:
    """
    Computes running sample mean and variance (using Welford's algorithm),
    which then allows computation of confidence intervals (CIs).

    The statistics are referred to as "online" as they are computed via updates
    to it's value, rather than storing lots of data and repeatedly taking the
    mean after new values have been added.

    Attributes:
        n (int):
            Number of data points processed.
        x_i (float):
            Most recent data point.
        mean (float):
            Running mean.
        _sq (float):
            Sum of squared differences from the mean.
        alpha (float):
            Significance level for confidence interval calculations.
        _observers (list):
            List of observer objects.
    """
    def __init__(self, data=None, alpha=0.1, observer=None):
        """
        Initialises the OnlineStatistics instance.

        Arguments:
            data (np.ndarray, optional):
                Array containing an initial data sample.
            alpha (float, optional):
                Significance level for confidence interval calculations.
            observer (object, optional):
                Observer to notify on updates.
        """
        self.n = 0
        self.x_i = None
        self.mean = None
        self._sq = None
        self.alpha = alpha
        self._observers = []

        # If an observer is supplied, then add it to the observer list
        if observer is not None:
            self.register_observer(observer)

        # If an array of initial values are supplied, then run update()
        if data is not None:
            if isinstance(data, np.ndarray):
                for x in data:
                    self.update(x)
            # Raise an error if in different format - else will invisibly
            # proceed and won't notice it hasn't done this
            else:
                raise ValueError(
                    f'data must be np.ndarray but is type {type(data)}')

    def register_observer(self, observer):
        """
        Registers an observer to be notified of updates.

        Arguments:
            observer (object):
                Observer to notify on updates.
        """
        self._observers.append(observer)

    def update(self, x):
        """
        Running update of mean and variance implemented using Welford's
        algorithm (1962).

        See Knuth. D `The Art of Computer Programming` Vol 2. 2nd ed. Page 216.

        Arguments:
            x (float):
                A new data point.
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
        Notify all registered observers about an update.
        """
        for observer in self._observers:
            observer.update(self)

    @property
    def variance(self):
        """
        Computes and returns the variance of the data points.
        """
        # Sum of squares of differences from the current mean divided by n - 1
        return self._sq / (self.n - 1)

    @property
    def std(self):
        """
        Computes and returns the standard deviation, or NaN if not enough data.
        """
        if self.n > 2:
            return np.sqrt(self.variance)
        return np.nan

    @property
    def std_error(self):
        """
        Computes and returns the standard error of the mean.
        """
        return self.std / np.sqrt(self.n)

    @property
    def half_width(self):
        """
        Computes and returns the half-width of the confidence interval.
        """
        dof = self.n - 1
        t_value = t.ppf(1 - (self.alpha / 2), dof)
        return t_value * self.std_error

    @property
    def lci(self):
        """
        Computes and returns the lower confidence interval bound, or NaN if
        not enough data.
        """
        if self.n > 2:
            return self.mean - self.half_width
        return np.nan

    @property
    def uci(self):
        """
        Computes and returns the upper confidence interval bound, or NaN if
        not enough data.
        """
        if self.n > 2:
            return self.mean + self.half_width
        return np.nan

    @property
    def deviation(self):
        """
        Computes and returns the precision of the confidence interval
        expressed as the percentage deviation of the half width from the mean.
        """
        if self.n > 2:
            return self.half_width / self.mean
        return np.nan


class ReplicationTabulizer:
    """
    Observes and records results from OnlineStatistics, updating each time new
    data is processed.

    Attributes:
        n (int):
            Number of data points processed.
        x_i (list):
            List containing each data point.
        cumulative_mean (list):
            List of the running mean.
        stdev (list):
            List of the standard deviation.
        lower (list):
            List of the lower confidence interval bound.
        upper (list):
            List of the upper confidence interval bound.
        dev (list):
            List of the percentage deviation of the confidence interval
            half width from the mean.
    """
    def __init__(self):
        """
        Initialises empty lists for storing statistics, and n is set to zero.
        """
        self.n = 0
        self.x_i = []
        self.cumulative_mean = []
        self.stdev = []
        self.lower = []
        self.upper = []
        self.dev = []

    def update(self, results):
        """
        Add new results from OnlineStatistics to the appropriate lists.

        Arguments:
            results (OnlineStatistics):
                An instance of OnlineStatistics containing updated statistical
                measures like the mean, standard deviation and confidence
                intervals.
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
        Create a results table from the stored lists.

        Returns:
             results (pd.DataFrame):
                Dataframe summarising the replication statistics.
        """
        results = pd.DataFrame(
            {
                'replications': np.arange(1, self.n + 1),
                'data': self.x_i,
                'cumulative_mean': self.cumulative_mean,
                'stdev': self.stdev,
                'lower_ci': self.lower,
                'upper_ci': self.upper,
                'deviation': self.dev
            }
        )
        return results


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ReplicationsAlgorithm:
    """
    Implements an adaptive replication algorithm for selecting the
    appropriate number of simulation replications based on statistical
    precision.

    Uses the "Replications Algorithm" from Hoad, Robinson, & Davies (2010).
    Given a model's performance measure and a user-set confidence interval
    half width prevision, automatically select the number of replications.
    Combines the "confidence intervals" method with a sequential look-ahead
    procedure to determine if a desired precision in the confidence interval
    is maintained.

    Attributes:
        alpha (float):
            Significance level for confidence interval calculations.
        half_width_precision (float):
            The target half width precision for the algorithm (i.e. percentage
            deviation of the confidence interval from the mean).
        initial_replications (int):
            Number of initial replications to perform.
        look_ahead (int):
            Minimum additional replications to look ahead to assess stability
            of precision. When the number of replications is <= 100, the value
            of look_ahead is used. When they are > 100, then
            look_ahead / 100 * max(n, 100) is used.
        replication_budget (int):
            Maximum allowed replications. Use for larger models where
            replication runtime is a constraint.
        verbose (bool):
            Whether to print progress information.
        n (int):
            Current number of replications performed.
        _n_solution (int):
            Final determined number of replications required for maintained
            precision.
        observer (object):
            Observer to notify on updates.
        stats (OnlineStatistics):
            Instance of OnlineStatistics, set in the select() method.
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments
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
        Initialise an instance of the ReplicationsAlgorithm.

        Arguments are described in the class docstring.
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
        self.stats = None

        # Check validity of provided parameters
        self.valid_inputs()

    def valid_inputs(self):
        """
        Checks validity of provided parameters.
        """
        for p in [self.initial_replications, self.look_ahead]:
            if not isinstance(p, int) or p < 0:
                raise ValueError(f'{p} must be a non-negative integer.')

        if self.half_width_precision <= 0:
            raise ValueError('half_width_precision must be greater than 0.')

        if self.replication_budget < self.initial_replications:
            raise ValueError(
                'replication_budget must be less than initial_replications.')

    def _klimit(self):
        """
        Determines the number of additional replications to check after
        precision is reached, scaling with total replications if they are
        greater than 100.

        Returns:
            int:
                Number of additional replications to verify stability.
        """
        return int((self.look_ahead / 100) * max(self.n, 100))

    def select(self, runner, metric):
        """
        Executes the replication algorithm, determining the necessary number
        of replications to achieve and maintain the desired precision.

        Arguments:
            runner (Runner):
                An instance of Runner which executes the model replications.
            metric (str):
                Name of the performance measure being tracked.

        Returns:
            int:
                The determined number of replications needed for precision.
        """

        converged = False

        # Run initial replications and collect results for the specified metric
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
    metric,
    alpha=0.05,
    desired_precision=0.05,
    min_rep=5
):
    """
    The confidence interval method for selecting the number of replications.

    This method will run the model for the specified number of replications.
    It then calculates the cumulative  mean and confidence intervals with
    each of those replications. It then checks the results to find when the
    precision is first achieved. It does not check if this precision is
    maintained.

    Arguments:
        replications (int):
            Number of times to run the model.
        metric (str):
            Name of performance metric to assess.
        alpha (float, optional):
            Significance level for confidence interval calculations.
        desired_precision (float, optional):
            The target half width precision (i.e. percentage deviation of the
            confidence interval from the mean).
        min_rep (int, optional):
            Minimum number of replications before checking precision. Useful
            when the number of replications returned does not provide a stable
            precision below target.

    Returns:
        tuple[int, pd.DataFrame]:
            - The minimum number of replications required to meet the
              precision. Returns -1 if precision is not achieved.
            - DataFrame containing cumulative statistics for each replication.

    Warnings:
        Issues a warning if the desired precision is not met within the
        provided replications.
    """
    # Run model for specified number of replications
    param = Param(number_of_runs=replications)
    choose_rep = Runner(param)
    choose_rep.run_reps()

    # Extract replication results for the specified metric
    rep_res = choose_rep.run_results_df[metric]

    # Set up method for calculating statistics and saving them as a table
    observer = ReplicationTabulizer()
    stats = OnlineStatistics(
        alpha=alpha, data=np.array(rep_res[:2]), observer=observer)

    # Calculate statistics with each replication, and get summary table
    for i in range(2, len(rep_res)):
        stats.update(rep_res[i])
    results = observer.summary_table()

    # Get minimum number of replications where deviation is less than target
    try:
        n_reps = (
            results.iloc[min_rep:]
            .loc[results['deviation'] <= desired_precision]
            .iloc[0]
            .name
        )
        print(f'Reached desired precision ({desired_precision}) in ' +
              f'{n_reps} replications.')
    # Return warning if there are no replications with the desired precision
    except IndexError:
        message = 'WARNING: the replications do not reach desired precision'
        warnings.warn(message)
        n_reps = -1

    return n_reps, results


def confidence_interval_method_simple(
    replications, metric, desired_precision=0.05, min_rep=5
):
    """
    Simple implementation using the confidence interval method to select the
    number of replications.

    This will produce the same results as confidence_interval_method(),
    but that depends on ReplicationTabulizer and OnlineStatistics, whilst
    this method using summary_stats(). These are both provided to give you
    a few options of possible ways to do this!

    Arguments:
        replications (int):
            Number of times to run the model.
        metric (string):
            Name of performance metric to assess.
        desired_precision (float, optional):
            The target half width precision (i.e. percentage deviation of the
            confidence interval from the mean).
        min_rep (int, optional):
            Minimum number of replications before checking precision. Useful
            when the number of replications returned does not provide a stable
            precision below target.

    Returns:
        tuple[int, pd.DataFrame]:
            - The minimum number of replications required to meet precision.
            - DataFrame containing cumulative statistics for each replication.

     Warnings:
        Issues a warning if the desired precision is not met within the
        provided replications.
    """
    # Run model for specified number of replications
    param = Param(number_of_runs=replications)
    choose_rep = Runner(param)
    choose_rep.run_reps()

    # If mean of metric is less than 1, multiply by 100
    df = choose_rep.run_results_df
    if df[metric].mean() < 1:
        df[f'adj_{metric}'] = df[metric] * 100
        metric = f'adj_{metric}'

    # Compute cumulative statistics
    cumulative = pd.DataFrame([
        {
            'replications': i + 1,  # Adjusted as counted from zero
            'data': df[metric][i],
            'cumulative_mean': stats[0],
            'stdev': stats[1],
            'lower_ci': stats[2],
            'upper_ci': stats[3],
            'deviation': (stats[3] - stats[0]) / stats[0]
        }
        for i, stats in enumerate(
            (summary_stats(df[metric].iloc[:i])
             for i in range(1, replications + 1))
        )
    ])

    # Get minimum number of replications where deviation is less than target
    try:
        n_reps = (
            cumulative.iloc[min_rep:]
            .loc[cumulative['deviation'] <= desired_precision]
            .iloc[0]
            .name
        ) + 1
        print(f'Reached desired precision ({desired_precision}) in ' +
              f'{n_reps} replications.')
    # Return warning if there are no replications with the desired precision
    except IndexError:
        warnings.warn(f'Running {replications} replications did not reach' +
                      f'desired precision ({desired_precision}).')
        n_reps = -1

    return n_reps, cumulative


def plotly_confidence_interval_method(
    n_reps, conf_ints, metric_name, figsize=(1200, 400), file_path=None
):
    """
    Generates an interactive Plotly visualisation of confidence intervals
    with increasing simulation replications.

    Arguments:
        n_reps (int):
            The number of replications required to meet the desired precision.
        conf_ints (pd.DataFrame):
            A DataFrame containing confidence interval statistics, including
            cumulative mean, upper/lower bounds, and deviations. As returned
            by ReplicationTabulizer summary_table() method.
        metric_name (str):
            Name of metric being analysed.
        figsize (tuple, optional):
            Plot dimensions in pixels (width, height).
        file_path (str):
            Path and filename to save the plot to.
    """
    fig = go.Figure()

    # Calculate relative deviations [1][4]
    deviation_pct = (
        (conf_ints['upper_ci'] - conf_ints['cumulative_mean'])
        / conf_ints['cumulative_mean']
        * 100
    ).round(2)

    # Confidence interval bands with hover info
    for col, color, dash in zip(
        ['lower_ci', 'upper_ci'],
        ['lightblue', 'lightblue'], ['dot', 'dot']
    ):
        fig.add_trace(
            go.Scatter(
                x=conf_ints['replications'],
                y=conf_ints[col],
                line={'color': color, 'dash': dash},
                name=col,
                text=['Deviation: {d}%' for d in deviation_pct],
                hoverinfo='x+y+name+text',
            )
        )

    # Cumulative mean line with enhanced hover
    fig.add_trace(
        go.Scatter(
            x=conf_ints['replications'],
            y=conf_ints['cumulative_mean'],
            line={'color': 'blue', 'width': 2},
            name='Cumulative Mean',
            hoverinfo='x+y+name',
        )
    )

    # Vertical threshold line
    fig.add_shape(
        type='line',
        x0=n_reps,
        x1=n_reps,
        y0=0,
        y1=1,
        yref='paper',
        line={'color': 'red', 'dash': 'dash'},
    )

    # Configure layout
    fig.update_layout(
        width=figsize[0],
        height=figsize[1],
        yaxis_title=f'Cumulative Mean: {metric_name}',
        hovermode='x unified',
        showlegend=True,
    )

    # Save figure
    if file_path is not None:
        fig.write_image(file_path)

    return fig
