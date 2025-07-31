"""
Testing of the simulation model using an MMS queue

Note that simulation will need to be run for suitable warm-up period in order to be comparable
Here we choose a large one to be sure.

"""

import math
from typing import Union
import numpy as np
import pandas as pd
import pytest

from simulation import confidence_interval_method, Param, Runner, run_scenarios



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
    
    Attributes:
        arrival_rate (float): Customer arrival rate (λ)
        service_rate (float): Service rate per server (μ)  
        num_servers (int): Number of servers (s)
        rho (float): Traffic intensity (utilization factor)
        metrics (dict): Dictionary of performance metrics
    """
    
    def __init__(self, arrival_rate: float, service_rate: float, num_servers: int) -> None:
        """
        Initialize the M/M/S queue.
        
        Args:
            arrival_rate: The arrival rate of customers (λ > 0)
            service_rate: The service rate per server (μ > 0)  
            num_servers: The number of servers (s >= 1)
            
        Raises:
            ValueError: If parameters are invalid or system is unstable
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
        
        Returns:
            Traffic intensity ρ = λ/(s*μ)
        """
        return self.arrival_rate / (self.num_servers * self.service_rate)  
    
    def _calculate_metrics(self) -> dict[str, float]:
        """
        Calculate all performance metrics for the queue.
        
        Returns:
            Dictionary containing performance metrics
        """
        metrics = {}
        metrics['ρ'] = self.rho
        metrics['L_q'] = self._get_mean_queue_length()
        metrics['L_s'] = metrics['L_q'] + (self.arrival_rate / self.service_rate)
        metrics['W_s'] = metrics['L_s'] / self.arrival_rate
        metrics['W_q'] = metrics['W_s'] - (1 / self.service_rate)
        return metrics
    
    def _get_mean_queue_length(self) -> float:
        """
        Calculate the expected number of customers waiting in queue (L_q).
        
        Uses the formula:
        L_q = P₀ * (λ/μ)^s * ρ / (s! * (1-ρ)²)
        
        Returns:
            Expected queue length
        """
        p0 = self.prob_system_empty()
        lambda_over_mu = self.arrival_rate / self.service_rate
        
        lq = (p0 * (lambda_over_mu ** self.num_servers) * self.rho) / \
             (math.factorial(self.num_servers) * (1 - self.rho) ** 2)
        
        return lq
        
    def prob_system_empty(self) -> float:
        """
        Calculate the probability that the system is empty (P₀).
        
        Uses the formula:
        P₀ = [Σ(n=0 to s-1) (λ/μ)^n/n! + (λ/μ)^s/(s!(1-ρ))]^(-1)
        
        Returns:
            Probability that system is empty
        """
        lambda_over_mu = self.arrival_rate / self.service_rate
        
        # Sum for n = 0 to s-1  
        sum_part = sum((lambda_over_mu ** n) / math.factorial(n) 
                      for n in range(self.num_servers))
        
        # Term for n >= s
        server_term = ((lambda_over_mu ** self.num_servers) / 
                      (math.factorial(self.num_servers) * (1 - self.rho)))
        
        return 1 / (sum_part + server_term)
    
    def prob_n_in_system(
        self, 
        n: int, 
        return_all_solutions: bool = True, 
        as_frame: bool = True
    ) -> Union[float, np.ndarray, pd.DataFrame]:
        """
        Calculate the probability of having n customers in the system.

        Args:
            n: Number of customers in the system (n >= 0)
            return_all_solutions: If True, return probabilities for 0,1,...,n
            as_frame: If True and return_all_solutions=True, return as DataFrame
            
        Returns:
            If return_all_solutions=False: Single probability P(N=n)
            If return_all_solutions=True: Array/DataFrame of probabilities 
            P(N=0) to P(N=n)
            
        Raises:
            ValueError: If n < 0
        """
        if n < 0:
            raise ValueError("n must be non-negative")
            
        p0 = self.prob_system_empty()
        lambda_over_mu = self.arrival_rate / self.service_rate
        probs = [p0]

        # For n = 1 to min(s, n)
        for i in range(1, min(self.num_servers + 1, n + 1)):
            pn = ((lambda_over_mu ** i) / math.factorial(i)) * p0
            probs.append(pn)

        # For n > s  
        for i in range(self.num_servers + 1, n + 1):
            pn = ((lambda_over_mu ** i) / 
                  (math.factorial(self.num_servers) * (self.num_servers ** (i - self.num_servers)))) * p0
            probs.append(pn)

        if return_all_solutions:
            results = np.array(probs)
            if as_frame:
                index = [f'P(N={i})' for i in range(len(results))]
                return pd.DataFrame(results, index=index, columns=['Probability'])
            else:
                return results
        else:
            return probs[n] if n < len(probs) else 0.0
        
    def summary_frame(self) -> pd.DataFrame:
        """
        Return performance metrics as a formatted DataFrame.
        
        Returns:
            DataFrame with performance metrics and descriptions
        """
        descriptions = {
            'ρ': 'Server utilization (traffic intensity)',
            'L_q': 'Expected number in queue',
            'L_s': 'Expected number in system', 
            'W_q': 'Expected waiting time in queue',
            'W_s': 'Expected time in system'
        }
        
        df = pd.DataFrame({
            'Value': list(self.metrics.values()),
            'Description': [descriptions[k] for k in self.metrics.keys()]
        }, index=list(self.metrics.keys()))
        
        return df
    
    @property 
    def total_in_system(self) -> float:
        """Expected number of customers in the system (L_s)."""
        return self.metrics['L_s']
    
    @property
    def avg_queue_length(self) -> float:
        """Expected number of customers in queue (L_q).""" 
        return self.metrics['L_q']
        
    @property
    def avg_wait_time(self) -> float:
        """Expected waiting time in queue (W_q)."""
        return self.metrics['W_q']
        
    @property
    def avg_system_time(self) -> float:
        """Expected total time in system (W_s)."""
        return self.metrics['W_s']



def run_simulation():
    # Define model parameters
    param = Param(
        patient_inter=4,
        mean_n_consult_time = 10,
        number_of_nurses = 4,
        warm_up_period = 500,
        data_collection_period = 1500,
        number_of_runs=100,
        audit_interval = 50,
        scenario_name = 0,
        cores = 1
    )

    # Run the replications
    experiment = Runner(param)
    experiment.run_reps()

   

    kpi_mapping = {
        "mean_q_time_nurse": "wq",
        "mean_time_with_nurse": "ws",
        "mean_nurse_utilisation": "rho",
        "mean_nurse_q_length": "lq"
    }


     # results
    return experiment.overall_results_df.T['mean'], kpi_mapping




results, map = run_simulation()
print(results)