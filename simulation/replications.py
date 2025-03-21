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
        observer (list):
            object to notify on updates.

    Acknowledgements:
        - Class adapted from Monks 2021.
    """
    def __init__(self, data=None, alpha=0.05, observer=None):
        """
        Initialises the OnlineStatistics instance.

        Arguments:
            data (np.ndarray, optional):
                Array containing an initial data sample.
            alpha (float, optional):
                Significance level for confidence interval calculations. For
                example, if alpha is 0.05, then the confidence level is 95%.
            observer (object, optional):
                Observer to notify on updates.
        """
        self.n = 0
        self.x_i = None
        self.mean = None
        self._sq = None
        self.alpha = alpha
        self.observer = observer

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

        # Run the observer update() method
        if self.observer is not None:
            self.observer.update(self)

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

    Acknowledgements:
        - Class adapted from Monks 2021.
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
        n (int):
            Current number of replications performed.

    Acknowledgements:
        - Class adapted from Monks 2021.
        - Implements algorithm from Hoad et al. 2010.
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        alpha=0.05,
        half_width_precision=0.05,
        initial_replications=3,
        look_ahead=5,
        replication_budget=1000
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

        # Initially set n to number of initial replications
        self.n = self.initial_replications

        # Check validity of provided parameters
        self.valid_inputs()

    def valid_inputs(self):
        """
        Checks validity of provided parameters.
        """
        for param_name in ['initial_replications', 'look_ahead']:
            param_value = getattr(self, param_name)
            if not isinstance(param_value, int) or param_value < 0:
                raise ValueError(f'{param_name} must be a non-negative ',
                                 f'integer, but provided {param_value}.')

        if self.half_width_precision <= 0:
            raise ValueError('half_width_precision must be greater than 0.')

        if self.replication_budget < self.initial_replications:
            raise ValueError(
                'replication_budget must be less than initial_replications.')

    def _klimit(self):
        """
        Determines the number of additional replications to check after
        precision is reached, scaling with total replications if they are
        greater than 100. Rounded down to nearest integer.

        Returns:
            int:
                Number of additional replications to verify stability.
        """
        return int((self.look_ahead / 100) * max(self.n, 100))

    def find_position(self, lst):
        """
        Find the first position where element is below deviation, and this is
        maintained through the lookahead period.

        This is used to correct the ReplicationsAlgorithm, which cannot return
        a solution below the initial_replications.

        Returns:
            int:
                Minimum replications required to meet and maintain precision.
        """
        # Check if the list is empty or if no value is below the threshold
        if not lst or all(x is None or x >= self.half_width_precision
                          for x in lst):
            return None

        # Find the first non-None value in the list
        start_index = pd.Series(lst).first_valid_index()

        # Iterate through the list, stopping when at last point where we still
        # have enough elements to look ahead
        if start_index is not None:
            for i in range(start_index, len(lst) - self.look_ahead):
                # Create slice of list with current value + lookahead
                # Check if all fall below the desired deviation
                if all(value < self.half_width_precision
                       for value in lst[i:i+self.look_ahead+1]):
                    # Add one, so it is the number of reps, as is zero-indexed
                    return i + 1
        return None

    # pylint: disable=too-many-branches
    def select(self, runner, metrics):
        """
        Executes the replication algorithm, determining the necessary number
        of replications to achieve and maintain the desired precision.

        Arguments:
            runner (Runner):
                An instance of Runner which executes the model replications.
            metrics (list):
                List of performance measure to track (should correspond to
                column names from the run results dataframe).

        Returns:
            tuple[dict, pd.DataFrame]:
                - A dictionary with the minimum number of replications required
                to meet the precision for each metric.
                - DataFrame containing cumulative statistics for each
                replication for each metric.

        Warnings:
            Issues a warning if the desired precision is not met for any
            metrics before the replication limit is met.
        """
        # Create instances of observers for each metric
        observers = {
            metric: ReplicationTabulizer()
            for metric in metrics}

        # Create dictionary to store record for each metric of:
        # - nreps (the solution - replications required for precision)
        # - target_met (record of how many times in a row the target has
        #   has been met, used to check if lookahead period has been passed)
        # - solved (whether it has maintained precision for lookahead)
        solutions = {
            metric: {'nreps': None,
                     'target_met': 0,
                     'solved': False} for metric in metrics}

        # If there are no initial replications, create empty instances of stats
        # for each metric...
        if self.initial_replications == 0:
            stats = {
                metric: OnlineStatistics(
                    alpha=self.alpha, observer=observers[metric])
                for metric in metrics
            }
        # If there are, run the replications, then create instances of stats
        # pre-loaded with data from the initial replications...
        # (we use run_reps() which allows for parallel processing if desired)
        else:
            stats = {}
            runner.param.number_of_runs = self.initial_replications
            runner.run_reps()
            for metric in metrics:
                stats[metric] = OnlineStatistics(
                    alpha=self.alpha,
                    observer=observers[metric],
                    data=np.array(runner.run_results_df[metric]))

        # After completing all replications, check if any have met precision,
        # add solution and update count
        for metric in metrics:
            if stats[metric].deviation <= self.half_width_precision:
                solutions[metric]['nreps'] = self.n
                solutions[metric]['target_met'] = 1
                # If there is no lookahead, mark as solved
                if self._klimit() == 0:
                    solutions[metric]['solved'] = True

        # Whilst have not yet got all metrics marked as solved = TRUE, and
        # still under replication budget + lookahead...
        while (
            sum(1 for v in solutions.values()
                if v['solved']) < len(metrics)
            and self.n < self.replication_budget + self._klimit()
        ):

            # Run another replication
            results = runner.run_single(self.n)['run']

            # Increment counter
            self.n += 1

            # Loop through the metrics...
            for metric in metrics:

                # If it is not yet solved...
                if not solutions[metric]['solved']:

                    # Update the running statistics for that metric
                    stats[metric].update(results[metric])

                    # If precision has been achieved...
                    if stats[metric].deviation <= self.half_width_precision:

                        # Check if target met the time prior - if not, record
                        # the solution.
                        if solutions[metric]['target_met'] == 0:
                            solutions[metric]['nreps'] = self.n

                        # Update how many times precision has been met in a row
                        solutions[metric]['target_met'] += 1

                        # Mark as solved if have finished lookahead period
                        if solutions[metric]['target_met'] > self._klimit():
                            solutions[metric]['solved'] = True

                    # If precision was not achieved, ensure nreps is None
                    # (e.g. in cases where precision is lost after a success)
                    else:
                        solutions[metric]['target_met'] = 0
                        solutions[metric]['nreps'] = None

        # Correction to result...
        for metric, dictionary in solutions.items():
            # Use find_position() to check for solution in initial replications
            adj_nreps = self.find_position(observers[metric].dev)
            # If there was a maintained solution, replace in solutions
            if adj_nreps is not None and dictionary['nreps'] is not None:
                if adj_nreps < dictionary['nreps']:
                    solutions[metric]['nreps'] = adj_nreps

        # Extract minimum replications for each metric
        nreps = {metric: value['nreps'] for metric, value in solutions.items()}

        # Combine observer summary frames into a single table
        summary_frame = pd.concat(
            [observer.summary_table().assign(metric=metric)
             for metric, observer in observers.items()]
        ).reset_index(drop=True)

        # Extract any metrics that were not solved and return warning
        if None in nreps.values():
            unsolved = [k for k, v in nreps.items() if v is None]
            warnings.warn(
                'WARNING: the replications did not reach the desired ' +
                f'precision for the following metrics: {unsolved}.')

        return nreps, summary_frame


# pylint: disable=too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-locals
def confidence_interval_method(
    replications,
    metrics,
    param=Param(),
    alpha=0.05,
    desired_precision=0.05,
    min_rep=3,
    verbose=False
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
        metrics (list):
            List of performance metrics to assess (should correspond to
            column names from the run results dataframe).
        param (Param):
            Instance of the parameter class with parameters to use (will use
            default parameters if not provided).
        alpha (float, optional):
            Significance level for confidence interval calculations.
        desired_precision (float, optional):
            The target half width precision (i.e. percentage deviation of the
            confidence interval from the mean).
        min_rep (int, optional):
            Minimum number of replications before checking precision. Useful
            when the number of replications returned does not provide a stable
            precision below target.
        verbose (bool, optional):
            Whether to print progress updates.

    Returns:
        tuple[dict, pd.DataFrame]:
            - A dictionary with the minimum number of replications required
            to meet the precision for each metric.
            - DataFrame containing cumulative statistics for each
            replication for each metric.

    Warnings:
        Issues a warning if the desired precision is not met within the
        provided replications.

    Acknowledgements:
        - Class adapted from Monks 2021.
    """
    # Replace runs in param with the specified number of replications
    param.number_of_runs = replications

    # Run the model
    choose_rep = Runner(param)
    choose_rep.run_reps()

    nreps_dict = {}
    summary_table_list = []

    for metric in metrics:
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

        # Get minimum number of replications where deviation is below target
        try:
            nreps = (
                (results
                 .loc[results['replications'] >= min_rep]
                 .loc[results['deviation'] <= desired_precision]
                 .iloc[0]
                 .replications)
            )
            if verbose:
                print(f'{metric}: Reached desired precision in {nreps} ' +
                      'replications.')
        # Return warning if there are no replications with desired precision
        except IndexError:
            message = f'WARNING: {metric} does not reach desired precision.'
            warnings.warn(message)
            nreps = None

        # Add solution to dictionary
        nreps_dict[metric] = nreps

        # Add metric name to table then append to list
        results['metric'] = metric
        summary_table_list.append(results)

    # Combine into a single table
    summary_frame = pd.concat(summary_table_list)

    return nreps_dict, summary_frame


def confidence_interval_method_simple(
    replications, metrics, param=Param(), desired_precision=0.05, min_rep=3,
    verbose=False
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
        metrics (list):
            List of performance metrics to assess.
        param (Param):
            Instance of the parameter class with parameters to use (will use
            default parameters if not provided).
        desired_precision (float, optional):
            The target half width precision (i.e. percentage deviation of the
            confidence interval from the mean).
        min_rep (int, optional):
            Minimum number of replications before checking precision. Useful
            when the number of replications returned does not provide a stable
            precision below target.
        verbose (bool, optional):
            Whether to print progress updates.

    Returns:
        tuple[dict, pd.DataFrame]:
            - A dictionary with the minimum number of replications required
            to meet the precision for each metric.
            - DataFrame containing cumulative statistics for each
            replication for each metric.

     Warnings:
        Issues a warning if the desired precision is not met within the
        provided replications.
    """
    # Replace runs in param with the specified number of replications
    param.number_of_runs = replications

    # Run the model
    choose_rep = Runner(param)
    choose_rep.run_reps()
    df = choose_rep.run_results_df

    nreps_dict = {}
    summary_table_list = []

    for metric in metrics:
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

        # Get minimum number of replications where deviation is below target
        try:
            nreps = (
                (cumulative
                 .loc[cumulative['replications'] >= min_rep]
                 .loc[cumulative['deviation'] <= desired_precision]
                 .iloc[0]
                 .replications)
            )
            if verbose:
                print(f'{metric}: Reached desired precision in {nreps} ' +
                      'replications.')
        # Return warning if there are no replications with desired precision
        except IndexError:
            warnings.warn(f'Running {replications} replications did not ' +
                          f'reach desired precision ({desired_precision})' +
                          f'for metric {metric}.')
            nreps = None

        # Add solution to dictionary
        nreps_dict[metric] = nreps

        # Add metric name to table then append to list
        cumulative['metric'] = metric
        summary_table_list.append(cumulative)

    # Combine into a single table
    summary_frame = pd.concat(summary_table_list)

    return nreps_dict, summary_frame


def plotly_confidence_interval_method(
    conf_ints, metric_name, n_reps=None, figsize=(1200, 400), file_path=None
):
    """
    Generates an interactive Plotly visualisation of confidence intervals
    with increasing simulation replications.

    Arguments:
        conf_ints (pd.DataFrame):
            A DataFrame containing confidence interval statistics, including
            cumulative mean, upper/lower bounds, and deviations. As returned
            by ReplicationTabulizer summary_table() method.
        metric_name (str):
            Name of metric being analysed.
        n_reps (int, optional):
            The number of replications required to meet the desired precision.
        figsize (tuple, optional):
            Plot dimensions in pixels (width, height).
        file_path (str):
            Path and filename to save the plot to.

    Acknowledgements:
        - Function adapted from Monks 2021.
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
    if n_reps is not None:
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
        yaxis_title=f'Cumulative Mean:\n{metric_name}',
        hovermode='x unified',
        showlegend=True,
    )

    # Save figure
    if file_path is not None:
        fig.write_image(file_path)

    return fig
