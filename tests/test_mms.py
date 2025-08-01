"""
Validates a discrete event simulation of a healthcare M/M/S queue by comparing
simulation results to analytical queueing theory.

Metrics (using standard queueing theory notation):
- ρ (rho): utilisation
- L_q: mean queue length
- L_s: mean number of patients in system
- W_q: mean waiting
- W_s: mean time in system

Results must match theory with a 15% tolerance (accomodates stochasticity).
Tests are run across diverse parameter combinations and utilisation levels.
System stability requires arrival rate < number_of_servers * service_rate.
"""

import math
import pytest

from simulation import Param, Runner


class MMSQueue:
    """
    Analytical M/M/S queue formulas.

    Parameters
    ----------
    arrival_rate : float
        Customer arrival rate (λ).
    service_rate : float
        Service rate per server (μ).
    num_servers : int
        Number of servers (s).

    Attributes
    ----------
    rho : float
        Utilisation (λ / (sμ)).
    lambda_over_mu : float
        Arrival/service rate ratio (λ / μ).
    metrics : dict
        Calculated performance metrics.
    """

    def __init__(self, arrival_rate, service_rate, num_servers):
        """
        Initialise the M/M/S queue.

        Raises
        ------
        ValueError
            If parameters are invalid or system is unstable.
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

        # Calculate utilisation
        self.rho = self.get_traffic_intensity()

        # Check system stability
        if self.rho >= 1:
            raise ValueError(
                f"System is unstable: ρ = {self.rho:.4f} >= 1. "
                f"Need λ < s*μ ({arrival_rate} < {num_servers * service_rate})"
            )

        # Calculate λ/μ (average customers in service if infinite servers)
        self.lambda_over_mu = self.arrival_rate / self.service_rate

        # Calculate performance metrics using Little's Law
        self.metrics = self.calculate_metrics()

    def get_traffic_intensity(self):
        """
        Calculate the traffic intensity (server utilisation).

        Returns
        -------
        float
            Traffic intensity ρ = λ/(s*μ).
        """
        return self.arrival_rate / (self.num_servers * self.service_rate)

    def calculate_metrics(self):
        """
        Calculate all performance metrics for the queue.

        Returns
        -------
        dict[str, float]
            Dictionary containing performance metrics.
        """
        metrics = {}
        metrics["rho"] = self.rho
        metrics["L_q"] = self.get_mean_queue_length()
        metrics["L_s"] = metrics["L_q"] + (
            self.arrival_rate / self.service_rate
        )
        metrics["W_s"] = metrics["L_s"] / self.arrival_rate
        metrics["W_q"] = metrics["W_s"] - (1 / self.service_rate)
        return metrics

    def get_mean_queue_length(self):
        """
        Calculate the expected number of customers waiting in queue (L_q).

        Uses the formula:
        L_q = P₀ * (λ/μ)^s * ρ / (s! * (1-ρ)²)

        Returns
        -------
        float
            Expected queue length.
        """
        p0 = self.prob_system_empty()

        lq = (p0 * (self.lambda_over_mu**self.num_servers) * self.rho) / (
            math.factorial(self.num_servers) * (1 - self.rho) ** 2
        )

        return lq

    def prob_system_empty(self):
        """
        Calculate the probability that the system is empty (P₀).

        Uses the formula:
        P₀ = [Σ(n=0 to s-1) (λ/μ)^n/n! + (λ/μ)^s/(s!(1-ρ))]^(-1)

        Returns
        -------
        float
            Probability that system is empty.
        """
        # Sum for n = 0 to s-1
        sum_part = sum(
            (self.lambda_over_mu**n) / math.factorial(n)
            for n in range(self.num_servers)
        )

        # Term for n >= s
        server_term = (self.lambda_over_mu**self.num_servers) / (
            math.factorial(self.num_servers) * (1 - self.rho)
        )

        return 1 / (sum_part + server_term)


def run_simulation_model(
    patient_inter,
    mean_n_consult_time,
    number_of_nurses
):
    """
    Run simulation and return key performance indicators using standard
    queueing theory notation.

    The warm-up period should be sufficiently long to allow the system
    to reach steady-state before data collection begins.
    """
    param = Param(
        patient_inter=patient_inter,
        mean_n_consult_time=mean_n_consult_time,
        number_of_nurses=number_of_nurses,
        warm_up_period=500,
        data_collection_period=1500,
        number_of_runs=100,
        audit_interval=50,
        scenario_name=0,
        cores=1,
    )
    experiment = Runner(param)
    experiment.run_reps()

    # Rename the columns using queuing theory notation
    mapping = {
        "mean_q_time_nurse": "W_q",
        "mean_time_in_system": "W_s",
        "mean_nurse_utilisation": "rho",
        "mean_nurse_q_length": "L_q",
    }
    df = experiment.overall_results_df.rename(columns=mapping)

    # Return relevant columns
    return df[mapping.values()].T["mean"]


@pytest.mark.parametrize(
    "patient_inter,mean_n_consult_time,number_of_nurses",
    [
        # Test case 1: Low utilisation (ρ ≈ 0.3)
        (10, 3, 2),
        # Test case 2: Medium utilisation (ρ ≈ 0.67)
        (6, 4, 2),
        # Test case 3: M/M/1 (ρ = 0.75)
        (4, 3, 1),
        # Test case 4: Multiple servers, high utilisation (ρ ≈ 0.91)
        (5.5, 5, 3),
        # Test case 5: Balanced system (ρ = 0.5)
        (8, 4, 1),
        # Test case 6: Many servers, low individual utilisation (ρ ≈ 0.63)
        (4, 10, 4),
        # Test case 7: Very low utilisation (ρ ≈ 0.167)
        (60, 10, 15),
    ],
)
def test_simulation_against_theory(
    patient_inter,
    mean_n_consult_time,
    number_of_nurses
):
    """Test simulation results against theoretical M/M/S queue calculations."""

    # Create theoretical M/M/S queue model and get metrics
    lam = 1 / patient_inter
    mu = 1 / mean_n_consult_time
    theory = MMSQueue(lam, mu, number_of_nurses).metrics

    # Run simulation
    sim = run_simulation_model(
        patient_inter=patient_inter,
        mean_n_consult_time=mean_n_consult_time,
        number_of_nurses=number_of_nurses
    )

    # Compare results with appropriate tolerance (round to 3dp + 15% tolerance)
    metrics = [
        ("rho", "Utilisation"),
        ("L_q", "Queue length"),
        ("W_q", "Wait time"),
        ("W_s", "System time")
    ]
    for key, label in metrics:
        sim_val = round(sim[key], 3)
        theory_val = round(theory[key], 3)
        assert sim_val == pytest.approx(theory_val, rel=0.15), (
            f"{label} mismatch: sim={sim_val}, theory={theory_val}"
        )
