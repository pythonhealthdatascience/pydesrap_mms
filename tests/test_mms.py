"""
Simulation Model Validation Using M/M/S Queueing Theory
======================================================

This module provides validation testing for a discrete event simulation model
of a healthcare queueing system by comparing simulation results against
theoretical M/M/S queueing theory calculations.

Overview
--------
The module implements both analytical and simulation-based approaches to
modeling a healthcare system where patients arrive for nurse consultations.
The system is modeled as an M/M/S queue with:

- **Markovian arrivals**: Patients arrive according to a Poisson process
- **Markovian service**: Consultation times follow exponential distribution
- **S servers**: Multiple nurses available to serve patients
- **Infinite capacity**: No limit on queue length or patient population
- **FIFO discipline**: First-in-first-out queueing

Key Components
--------------
1. **MMSQueue Class**: Implements analytical M/M/S queueing theory formulas
   to calculate theoretical performance metrics including server utilization,
   queue lengths, and waiting times.

2. **Simulation Interface**: Functions to execute discrete event simulation
   runs with proper warm-up periods, multiple replications, and statistical
   analysis of results.

3. **Validation Tests**: Parametrized test suite that compares simulation
   outputs against theoretical predictions across various system configurations
   and utilization levels.

Performance Metrics
------------------
The module uses standard queueing theory notation:

- **ρ (rho)**: Server utilization / traffic intensity
- **L_q**: Expected number of customers waiting in queue
- **L_s**: Expected number of customers in system (queue + service)
- **W_q**: Expected waiting time in queue
- **W_s**: Expected total time in system

Validation Approach
------------------
Simulation results are validated by:

1. Running multiple independent replications to obtain statistical estimates
2. Using appropriate warm-up periods to eliminate initialization bias
3. Comparing mean simulation outputs against theoretical values
4. Testing across diverse parameter combinations and utilization levels
5. Applying relative tolerance bounds to account for simulation variability

Usage Notes
-----------
- The warm-up period should be sufficiently long for steady-state convergence
- Multiple replications provide confidence intervals for statistical validation
- System stability requires arrival rate < number_of_servers * service_rate
- Relative tolerance of 15% is used to accommodate simulation stochasticity

This validation framework ensures the simulation model accurately represents
the underlying queueing process and can be trusted for performance analysis
and capacity planning in healthcare systems.
"""

import math
from typing import Union
import numpy as np
import pandas as pd
import pytest

from simulation import Param, Runner


class MMSQueue:
    """
    M/M/S/∞/∞/FIFO Queueing System

    A queueing system with:
    - Markovian (Poisson) arrivals
    - Markovian (exponential) service times
    - S servers
    - Infinite system capacity
    - Infinite population
    - First-In-First-Out discipline

    Attributes
    ----------
    arrival_rate : float
        Customer arrival rate (λ)
    service_rate : float
        Service rate per server (μ)
    num_servers : int
        Number of servers (s)
    rho : float
        Traffic intensity (utilization factor)
    metrics : dict
        Dictionary of performance metrics
    """

    def __init__(
        self, arrival_rate: float, service_rate: float, num_servers: int
    ) -> None:
        """
        Initialize the M/M/S queue.

        Parameters
        ----------
        arrival_rate : float
            The arrival rate of customers (λ > 0)
        service_rate : float
            The service rate per server (μ > 0)
        num_servers : int
            The number of servers (s >= 1)

        Raises
        ------
        ValueError
            If parameters are invalid or system is unstable
        """
        if arrival_rate <= 0:
            raise ValueError("Arrival rate must be positive")
        if service_rate <= 0:
            raise ValueError("Service rate must be positive")
        if num_servers < 1:
            raise ValueError("Number of servers must be at least 1")

        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.num_servers = num_servers
        self.rho = self._get_traffic_intensity()

        # Check system stability
        if self.rho >= 1:
            raise ValueError(
                f"System is unstable: ρ = {self.rho:.4f} >= 1. "
                f"Need λ < s*μ ({arrival_rate} < {num_servers * service_rate})"
            )

        # Calculate performance metrics using Little's Law
        self.metrics = self._calculate_metrics()

    def _get_traffic_intensity(self) -> float:
        """
        Calculate the traffic intensity (server utilization).

        Returns
        -------
        float
            Traffic intensity ρ = λ/(s*μ)
        """
        return self.arrival_rate / (self.num_servers * self.service_rate)

    def _calculate_metrics(self) -> dict[str, float]:
        """
        Calculate all performance metrics for the queue.

        Returns
        -------
        dict[str, float]
            Dictionary containing performance metrics
        """
        metrics = {}
        metrics["ρ"] = self.rho
        metrics["L_q"] = self._get_mean_queue_length()
        metrics["L_s"] = metrics["L_q"] + (
            self.arrival_rate / self.service_rate
        )
        metrics["W_s"] = metrics["L_s"] / self.arrival_rate
        metrics["W_q"] = metrics["W_s"] - (1 / self.service_rate)
        return metrics

    def _get_mean_queue_length(self) -> float:
        """
        Calculate the expected number of customers waiting in queue (L_q).

        Uses the formula:
        L_q = P₀ * (λ/μ)^s * ρ / (s! * (1-ρ)²)

        Returns
        -------
        float
            Expected queue length
        """
        p0 = self.prob_system_empty()
        lambda_over_mu = self.arrival_rate / self.service_rate

        lq = (p0 * (lambda_over_mu**self.num_servers) * self.rho) / (
            math.factorial(self.num_servers) * (1 - self.rho) ** 2
        )

        return lq

    def prob_system_empty(self) -> float:
        """
        Calculate the probability that the system is empty (P₀).

        Uses the formula:
        P₀ = [Σ(n=0 to s-1) (λ/μ)^n/n! + (λ/μ)^s/(s!(1-ρ))]^(-1)

        Returns
        -------
        float
            Probability that system is empty
        """
        lambda_over_mu = self.arrival_rate / self.service_rate

        # Sum for n = 0 to s-1
        sum_part = sum(
            (lambda_over_mu**n) / math.factorial(n)
            for n in range(self.num_servers)
        )

        # Term for n >= s
        server_term = (lambda_over_mu**self.num_servers) / (
            math.factorial(self.num_servers) * (1 - self.rho)
        )

        return 1 / (sum_part + server_term)

    def prob_n_in_system(
        self, n: int, return_all_solutions: bool = True, as_frame: bool = True
    ) -> Union[float, np.ndarray, pd.DataFrame]:
        """
        Calculate the probability of having n customers in the system.

        Parameters
        ----------
        n : int
            Number of customers in the system (n >= 0)
        return_all_solutions : bool, default=True
            If True, return probabilities for 0,1,...,n
        as_frame : bool, default=True
            If True and return_all_solutions=True, return as DataFrame

        Returns
        -------
        float or np.ndarray or pd.DataFrame
            If return_all_solutions=False: Single probability P(N=n)
            If return_all_solutions=True: Array/DataFrame of probabilities
            P(N=0) to P(N=n)

        Raises
        ------
        ValueError
            If n < 0
        """
        if n < 0:
            raise ValueError("n must be non-negative")

        p0 = self.prob_system_empty()
        lambda_over_mu = self.arrival_rate / self.service_rate
        probs = [p0]

        # For n = 1 to min(s, n)
        for i in range(1, min(self.num_servers + 1, n + 1)):
            pn = ((lambda_over_mu**i) / math.factorial(i)) * p0
            probs.append(pn)

        # For n > s
        for i in range(self.num_servers + 1, n + 1):
            pn = (
                (lambda_over_mu**i)
                / (
                    math.factorial(self.num_servers)
                    * (self.num_servers ** (i - self.num_servers))
                )
            ) * p0
            probs.append(pn)

        if return_all_solutions:
            results = np.array(probs)
            if as_frame:
                index = [f"P(N={i})" for i in range(len(results))]
                return pd.DataFrame(
                    results, index=index, columns=["Probability"]
                )
            else:
                return results

        return probs[n] if n < len(probs) else 0.0

    def summary_frame(self) -> pd.DataFrame:
        """
        Return performance metrics as a formatted DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with performance metrics and descriptions
        """
        descriptions = {
            "ρ": "Server utilization (traffic intensity)",
            "L_q": "Expected number in queue",
            "L_s": "Expected number in system",
            "W_q": "Expected waiting time in queue",
            "W_s": "Expected time in system",
        }

        df = pd.DataFrame(
            {
                "Value": list(self.metrics.values()),
                "Description": [descriptions[k] for k in self.metrics.keys()],
            },
            index=list(self.metrics.keys()),
        )

        return df

    @property
    def total_in_system(self) -> float:
        """Expected number of customers in the system (L_s)."""
        return self.metrics["L_s"]

    @property
    def avg_queue_length(self) -> float:
        """Expected number of customers in queue (L_q)."""
        return self.metrics["L_q"]

    @property
    def avg_wait_time(self) -> float:
        """Expected waiting time in queue (W_q)."""
        return self.metrics["W_q"]

    @property
    def avg_system_time(self) -> float:
        """Expected total time in system (W_s)."""
        return self.metrics["W_s"]


def add_time_in_system_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add mean_time_in_system column to the dataframe.

    This column represents the total time a patient spends in the system,
    which is the sum of waiting time in queue and service time with nurse.

    Args:
        df: DataFrame containing simulation results

    Returns:
        DataFrame with added mean_time_in_system column
    """
    df_copy = df.copy()
    df_copy["mean_time_in_system"] = (
        df_copy["mean_q_time_nurse"] + df_copy["mean_time_with_nurse"]
    )
    return df_copy


def run_simulation_model(
    patient_inter: int = 4,
    mean_n_consult_time: float = 10.0,
    number_of_nurses: int = 4,
    warm_up_period: float = 500.0,
    data_collection_period: float = 1500.0,
    number_of_runs: int = 100,
    audit_interval: float = 50.0,
    scenario_name: int = 0,
    cores: int = -1,
) -> pd.Series:
    """
    Run multiple replications of an M/M/S queueing simulation model.

    This function executes a discrete event simulation of a healthcare system
    modeled as an M/M/S queue (Markovian arrivals, Markovian service times,
    S servers) and returns key performance indicators using standard queueing
    theory notation.

    The simulation models patients arriving for nurse consultations with:
    - Exponential inter-arrival times
    - Exponential service (consultation) times
    - Multiple nurses (servers)
    - FIFO queueing discipline

    Parameters
    ----------
    patient_inter : int, default=4
        Mean time between patient arrivals (minutes). Used as parameter
        for exponential inter-arrival time distribution.
    mean_n_consult_time : float, default=10.0
        Mean consultation time with nurse (minutes). Used as parameter
        for exponential service time distribution.
    number_of_nurses : int, default=4
        Number of nurses available to serve patients (number of servers).
    warm_up_period : float, default=500.0
        Duration of warm-up period (minutes) before data collection begins.
        Results from this period are discarded to avoid initialization bias.
    data_collection_period : float, default=1500.0
        Duration of data collection period (minutes) after warm-up.
        Performance metrics are calculated from this period only.
    number_of_runs : int, default=100
        Number of independent simulation replications to execute.
        More runs provide better statistical precision.
    audit_interval : float, default=50.0
        Time interval (minutes) for collecting intermediate statistics
        during simulation runs.
    scenario_name : int, default=0
        Identifier for the simulation scenario (for tracking purposes).
    cores : int, default=-1
        Number of CPU cores to utilize for parallel execution.
        If -1, uses all available cores.

    Returns
    -------
    pd.Series
        Series containing mean performance metrics across all replications,
        indexed with standard queueing theory notation:

        - 'W_q': Mean waiting time in queue (minutes)
        - 'W_s': Mean total time in system (minutes)
        - 'rho': Mean server (nurse) utilization (0-1)
        - 'L_q': Mean number of patients in queue

    Notes
    -----
    - The warm-up period should be sufficiently long to allow the system
      to reach steady-state before data collection begins
    - Results can be compared against theoretical M/M/S queue formulas
      to validate simulation model accuracy
    - System stability requires arrival_rate < number_of_nurses * service_rate

    """

    # col mapping to queuing theory notation
    # note that the simulation model does not directly output W_s
    # so we need to calculate W_s = mean_q_time_nurse + mean_time_with_nurse
    col_kpi_mapping = {
        "mean_q_time_nurse": "W_q",
        "mean_time_in_system": "W_s",
        "mean_nurse_utilisation": "rho",
        "mean_nurse_q_length": "L_q",
    }

    # Define model parameters
    param = Param(
        patient_inter=patient_inter,
        mean_n_consult_time=mean_n_consult_time,
        number_of_nurses=number_of_nurses,
        warm_up_period=warm_up_period,
        data_collection_period=data_collection_period,
        number_of_runs=number_of_runs,
        audit_interval=audit_interval,
        scenario_name=scenario_name,
        cores=cores,
    )

    # Run the replications
    experiment = Runner(param)
    experiment.run_reps()

    # Add the mean_time_in_system column before renaming
    comparable_results_df = add_time_in_system_column(
        experiment.overall_results_df
    )

    # rename columns and return only relevenat
    comparable_results_df = comparable_results_df.rename(
        columns=col_kpi_mapping
    )
    return comparable_results_df[col_kpi_mapping.values()].T["mean"]


@pytest.mark.parametrize(
    "patient_inter,mean_n_consult_time,number_of_nurses",
    [
        # Test case 1: Low utilization (ρ ≈ 0.3)
        (10, 3, 2),
        # Test case 2: Medium utilization (ρ ≈ 0.67)
        (6, 4, 2),
        # Test case 3: M/M/1 (ρ = 0.75)
        (4, 3, 1),
        # Test case 4: Multiple servers, high utilization (ρ ≈ 0.91)
        (5.5, 5.0, 3),
        # Test case 5: Balanced system (ρ = 0.5)
        (8, 4, 1),
        # Test case 6: Many servers, low individual utilization (ρ ≈ 0.63)
        (4, 10, 4),
        # Test case 7: Very low utilization (ρ ≈ 0.167)
        (60, 10, 15),
    ],
)
def test_simulation_against_theory(
    patient_inter: float,
    mean_n_consult_time: float,
    number_of_nurses: int,
    decimal_places: int = 3,
):
    """
    Test simulation results against theoretical M/M/S queue calculations.

    Parameters correspond to:
    - arrival_rate (λ) = 1 / patient_inter
    - service_rate (μ) = 1 / mean_n_consult_time
    - num_servers (s) = number_of_nurses
    """

    # Calculate theoretical results using MMSQueue
    arrival_rate = 1.0 / patient_inter
    service_rate = 1.0 / mean_n_consult_time

    # Create theoretical M/M/S queue model
    mms_queue = MMSQueue(
        arrival_rate=arrival_rate,
        service_rate=service_rate,
        num_servers=number_of_nurses,
    )

    # Get theoretical metrics
    theoretical_metrics = {
        "W_q": mms_queue.avg_wait_time,
        "W_s": mms_queue.avg_system_time,
        "rho": mms_queue.rho,
        "L_q": mms_queue.avg_queue_length,
    }

    # Run simulation
    simulation_results = run_simulation_model(
        patient_inter=patient_inter,
        mean_n_consult_time=mean_n_consult_time,
        number_of_nurses=number_of_nurses,
        number_of_runs=100,
    )

    relative_tolerance = 0.15

    # Compare results with appropriate tolerances (we round to 3 dp)
    assert round(simulation_results["rho"], decimal_places) == pytest.approx(
        round(theoretical_metrics["rho"], decimal_places),
        rel=relative_tolerance,
    ), (
        f"Utilization mismatch: sim={simulation_results['rho']:.3f}, "
        + f"theory={theoretical_metrics['rho']:.3f}"
    )

    # Queue length and wait times may have more variability (15% tolerance)
    assert round(simulation_results["L_q"], decimal_places) == pytest.approx(
        round(theoretical_metrics["L_q"], decimal_places),
        rel=relative_tolerance,
    ), (
        f"Queue length mismatch: sim={simulation_results['L_q']:.3f}, "
        + f"theory={theoretical_metrics['L_q']:.3f}"
    )

    assert round(simulation_results["W_q"], decimal_places) == pytest.approx(
        round(theoretical_metrics["W_q"], decimal_places),
        rel=relative_tolerance,
    ), (
        f"Wait time mismatch: sim={simulation_results['W_q']:.3f}, "
        + f"theory={theoretical_metrics['W_q']:.3f}"
    )

    assert round(simulation_results["W_s"], decimal_places) == pytest.approx(
        round(theoretical_metrics["W_s"], decimal_places),
        rel=relative_tolerance,
    ), (
        f"System time mismatch: sim={simulation_results['W_s']:.3f}, "
        + f"theory={theoretical_metrics['W_s']:.3f}"
    )
