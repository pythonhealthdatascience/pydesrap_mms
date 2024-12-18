"""Simple Reproducible SimPy Discrete-Event Simulation (DES) Model.

Uses object-oriented approach to create an M/M/c model with a warm-up
period, replications, seed control. For this example application, the time unit
is described as minutes, but this could be changed - for example, to hours,
days.

Credit:
    > This code is adapted from Sammi Rosser and Dan Chalk (2024) HSMA - the
    little book of DES (https://github.com/hsma-programme/hsma6_des_book)
    (MIT License).
    > The distribution class is copied from Tom Monks (2021) sim-tools:
    fundamental tools to support the simulation process in python
    (https://github.com/TomMonks/sim-tools) (MIT License). For other
    distributions (bernoulli, lognormal, normal, uniform, triangular, fixed,
    combination, continuous empirical, erlang, weibull, gamma, beta, discrete,
    truncated, raw empirical, pearsonV, pearsonVI, erlangK, poisson), check
    out the sim-tools package.

License:
    This project is licensed under the MIT License. See the LICENSE file for
    more details.

Typical usage example:

    trial = Trial(param=Defaults())
    trial.run_trial()
    print(trial.trial_results_df)
"""

from joblib import Parallel, delayed
import numpy as np
import pandas as pd
import scipy.stats as st
import simpy


class Defaults():
    """
    Default parameters for simulation.

    Attributes:
        patient_inter (float):
            Mean inter-arrival time between patients in minutes.
        mean_n_consult_time (float):
            Mean nurse consultation time in minutes.
        number_of_nurses (float):
            Number of available nurses.
        warm_up_period (int):
            Duration of the warm-up period in minutes - running simulation but
            not yet collecting results.
        data_collection_period (int):
            Duration of data collection period in minutes (also known as the
            measurement interval) - which begins after any warm-up period
        number_of_runs (int):
            The number of runs (also known as replications), defining how many
            times to re-run the simulation (with different random numbers).
        audit_interval (int):
            How frequently to audit resource utilisation, in minutes.
        scenario_name (int|float|string):
            Label for the scenario.
        cores (int):
            Number of CPU cores to use for parallel execution. Set to
            desired number, or to -1 to use all available cores. For
            sequential execution, set to 1 (default).
    """
    def __init__(self):
        """
        Initalise instance of parameters class.
        """
        # Disable restriction on attribute modification during initialisation
        object.__setattr__(self, '_initialising', True)

        self.patient_inter = 4
        self.mean_n_consult_time = 10
        self.number_of_nurses = 5
        self.warm_up_period = 1440*13  # 13 days
        self.data_collection_period = 1440*30  # 30 days
        self.number_of_runs = 31
        self.audit_interval = 120  # every 2 hours
        self.scenario_name = 0
        self.cores = -1

        # Re-enable attribute checks after initialisation
        object.__setattr__(self, '_initialising', False)

    def __setattr__(self, name, value):
        """
        Prevent addition of new attributes.

        Only allow modification of existing attributes, and not the addition
        of new attributes. This helps avoid an error where a parameter appears
        to have been changed, but remains the same as the attribute name
        used was incorrect.
        """
        # Skip the check if the object is still initialising
        if hasattr(self, '_initialising') and self._initialising:
            super().__setattr__(name, value)
        else:
            # Check if attribute of that name is already present
            if name in self.__dict__:
                super().__setattr__(name, value)
            else:
                raise AttributeError(
                    f'Cannot add new attribute "{name}" - only possible to ' +
                    f'modify existing attributes: {self.__dict__.keys()}')


def summary_stats(data):
    """
    Calculate mean, standard deviation and 95% confidence interval (CI).

    Arguments:
        data (pd.Series):
            Data to use in calculation
    Returns:
        tuple: (mean, standard deviation, CI lower, CI upper)
    """
    mean = data.mean()
    count = len(data)

    # Cannot calculate some metrics if there is only 1 sample in data
    if count == 1:
        std_dev = np.nan
        ci_lower = np.nan
        ci_upper = np.nan
    else:
        std_dev = data.std()
        # Calculation of CI uses t-distribution, which is suitable for
        # smaller sample sizes (n<30)
        ci_lower, ci_upper = st.t.interval(
            confidence=0.95,
            df=count-1,
            loc=mean,
            scale=st.sem(data))

    return mean, std_dev, ci_lower, ci_upper


class Patient:
    """
    Represents a patient.

    Attributes:
        patient_id (int):
            Patient's unique identifier.
        arrival_time (float):
            Arrival time for the patient in minutes.
        q_time_nurse (float):
            Time the patient spent waiting for a nurse in minutes.
        time_with_nurse (float):
            Time spent in consultation with a nurse in minutes.
    """
    def __init__(self, patient_id):
        """
        Initialises a new patient.

        Arguments:
            patient_id (int):
                Patient's unique identifier.
        """
        self.patient_id = patient_id
        self.arrival_time = np.nan
        self.q_time_nurse = np.nan
        self.time_with_nurse = np.nan


class Exponential:
    """
    Generate samples from an exponential distribution.

    Attributes:
        mean (float):
            Mean of the exponential distribution.
        random_seed (int|None):
            Random seed to reproduce samples.
        size (int|None):
            Number of samples to return. If set to none, then returns a single
            sample.
    """
    def __init__(self, mean, random_seed):
        """
        Initialises a new distribution.

        Arguments:
            mean (float):
                Mean of the exponential distribution.
            random_seed (int|None):
                Random seed to reproduce samples.
        """
        self.mean = mean
        self.rand = np.random.default_rng(random_seed)

    def sample(self, size=None):
        """
        Generate sample.

        Arguments:
            size (int|None):
                Number of samples to return. If set to none, then returns a
                single sample.
        """
        return self.rand.exponential(self.mean, size=size)


class Model:
    """
    Simulation model for a clinic.

    In this model, patients arrive at the clinic, wait for an available
    nurse, have a consultation with the nurse, and then leave.

    Attributes:
        param (Defaults):
            Simulation parameters.
        run_number (int):
            Run number for random seed generation.
        env (simpy.Environment):
            The SimPy environment for the simulation.
        nurse (simpy.Resource):
            SimPy resource representing nurses.
        patients (list):
            List containing the generated patient objects.
        nurse_time_used (float):
            Total time the nurse resources have been used in minutes.
        nurse_consult_count (int):
            Count of patients seen by nurse, using to calculate running mean
            wait time.
        running_mean_nurse_wait (float):
            Running mean wait time for nurse during simulation in minutes,
            calculated using Welford's Running Average.
        audit_list (list):
            List to store metrics recorded at regular intervals.
        results_list (list):
            List of dictionaries with the results for each patient (as defined
            by their patient object attributes).
        patient_inter_arrival_dist (Exponential):
            Distribution for sampling patient inter-arrival times.
        nurse_consult_time_dist (Exponential):
            Distribution for sampling nurse consultation times.
    """
    def __init__(self, param, run_number):
        """
        Initalise a new model.

        Arguments:
            param (Defaults, optional):
                Simulation parameters. Defaults to new instance of the
                Defaults() class.
            run_number (int, optional):
                Run number for random seed generation. Defaults to 0.
        """
        # Set parameters and run number
        self.param = param
        self.run_number = run_number

        # Create simpy environment and resource
        self.env = simpy.Environment()
        self.nurse = simpy.Resource(self.env,
                                    capacity=self.param.number_of_nurses)

        # Initialise attributes to store results
        self.patients = []
        self.nurse_time_used = 0
        self.nurse_consult_count = 0
        self.running_mean_nurse_wait = 0
        self.audit_list = []
        self.results_list = []

        # Generate seeds based on run_number as entropy (the "starter" seed)
        # The seeds produced will create independent streams
        ss = np.random.SeedSequence(entropy=self.run_number)
        seeds = ss.spawn(2)

        # Initialise distributions using those seeds
        self.patient_inter_arrival_dist = Exponential(
            mean=self.param.patient_inter, random_seed=seeds[0])
        self.nurse_consult_time_dist = Exponential(
            mean=self.param.mean_n_consult_time, random_seed=seeds[1])

        # Define validation rules for attributes
        # Doesn't include number_of_nurses as this is tested by simpy.Resource
        validation_rules = {
            'positive': ['patient_inter', 'mean_n_consult_time',
                         'number_of_runs', 'audit_interval'],
            'non_negative': ['warm_up_period', 'data_collection_period']
        }
        # Iterate over the validation rules
        for rule, param_names in validation_rules.items():
            for param_name in param_names:
                # Get the value of the parameter by its name
                param_value = getattr(self.param, param_name)
                # Check if it meets the rules for that parameter
                if rule == 'positive' and param_value <= 0:
                    raise ValueError(
                        f'Parameter "{param_name}" must be greater than 0.'
                    )
                elif rule == 'non_negative' and param_value < 0:
                    raise ValueError(
                        f'Parameter "{param_name}" must be greater than or ' +
                        'equal to 0.'
                    )

    def generate_patient_arrivals(self):
        """
        Generate patient arrivals.
        """
        while True:
            # Create new patient, with ID based on length of patient list + 1
            p = Patient(len(self.patients) + 1)
            p.arrival_time = self.env.now

            # If the warm-up period has passed, add the patient to the list.
            # The list stores a reference to the patient object, so any updates
            # to the patient attributes will be reflected in the list as well
            if self.env.now >= self.param.warm_up_period:
                self.patients.append(p)

            # Start process of attending clinic
            self.env.process(self.attend_clinic(p))

            # Sample and pass time to next arrival
            sampled_inter = self.patient_inter_arrival_dist.sample()
            yield self.env.timeout(sampled_inter)

    def attend_clinic(self, patient):
        """
        Simulates the patient's journey through the clinic.

        Arguments:
            patient (Patient):
                Instance of the Patient() class representing a single patient.
        """
        # Start queueing and request nurse resource
        start_q_nurse = self.env.now
        with self.nurse.request() as req:
            yield req

            # Record time spent waiting
            patient.q_time_nurse = self.env.now - start_q_nurse

            # Update running mean of wait time for the nurse
            self.nurse_consult_count += 1
            self.running_mean_nurse_wait += (
               (patient.q_time_nurse - self.running_mean_nurse_wait) /
               self.nurse_consult_count
            )

            # Sample time spent with nurse
            patient.time_with_nurse = self.nurse_consult_time_dist.sample()

            # If warm-up period has passed, update the total nurse time used.
            # This is used to calculate utilisation. To avoid overestimation,
            # if the consultation would overrun the simulation, just record
            # time to end of the simulation.
            if self.env.now >= self.param.warm_up_period:
                remaining_time = (
                    self.param.warm_up_period +
                    self.param.data_collection_period) - self.env.now
                self.nurse_time_used += min(
                    patient.time_with_nurse, remaining_time)

            # Pass time spent with nurse
            yield self.env.timeout(patient.time_with_nurse)

    def interval_audit(self, interval):
        """
        Audit waiting times and resource utilisation at regular intervals.

        The running mean wait time is calculated using Welford's Running
        Average, which is a method that avoids the need to store previous wait
        times to compute the average. The running mean reflects the main wait
        time for all patients seen by nurse up to that point in the simulation.

        Arguments:
            interval (int, optional):
                Time between audits in minutes.
        """
        while True:
            # Only save results if the warm-up period has passed
            if self.env.now >= self.param.warm_up_period:
                self.audit_list.append({
                    'resource_name': 'nurse',
                    'simulation_time': self.env.now,
                    'utilisation': self.nurse.count / self.nurse.capacity,
                    'queue_length': len(self.nurse.queue),
                    'running_mean_wait_time': self.running_mean_nurse_wait
                })

            # Trigger next audit after desired interval has passed
            yield self.env.timeout(interval)

    def run(self):
        """
        Runs the simulation for the specified duration.
        """
        # Start patient generator
        self.env.process(self.generate_patient_arrivals())

        # Start interval auditor
        self.env.process(
            self.interval_audit(interval=self.param.audit_interval))

        # Run for specified duration (which is the warm-up period + the
        # data collection period)
        self.env.run(until=self.param.data_collection_period +
                     self.param.warm_up_period)

        # Convert list of patient objects into a list that just contains the
        # attributes of each of those patients as dictionaries
        self.results_list = [x.__dict__ for x in self.patients]


class Trial:
    """
    Manages multiple simulation runs.

    Attributes:
        param (Defaults):
            Simulation parameters.
        patient_results_df (pandas.DataFrame):
            Dataframe to store patient-level results.
        trial_results_df (pandas.DataFrame):
            Dataframe to store trial-level results.
        interval_audit_df (pandas.DataFrame):
            Dataframe to store interval audit results.
        overall_results_df (pandas.DataFrame):
            Dataframe to store average results from runs of the trial.
    """
    def __init__(self, param):
        '''
        Initialise a new instance of the trial class.

        Arguments:
            param (Defaults):
                Simulation parameters.
        '''
        # Store model parameters
        self.param = param
        # Initialise empty dataframes to store results
        self.patient_results_df = pd.DataFrame()
        self.trial_results_df = pd.DataFrame()
        self.interval_audit_df = pd.DataFrame()
        self.overall_results_df = pd.DataFrame()

    def run_single(self, run):
        """
        Executes a single simulation run and records the results.

        Arguments:
            run (int):
                The run number for the simulation

        Returns:
            dict:
                A dictionary containing the patient-level results, trial-level
                results, and interval audit results.
        """
        # Run model
        model = Model(param=self.param, run_number=run)
        model.run()

        # Convert patient-level results to a dataframe and add column with run
        patient_results = pd.DataFrame(model.results_list)
        patient_results['run'] = run

        # Create dictionary recording the trial-level results
        trial_results = {
            'run_number': run,
            'scenario': self.param.scenario_name,
            'arrivals': len(patient_results),
            'mean_q_time_nurse': patient_results['q_time_nurse'].mean(),
            'mean_time_with_nurse': patient_results['time_with_nurse'].mean(),
            'mean_nurse_utilisation': (model.nurse_time_used /
                                       (self.param.number_of_nurses *
                                        self.param.data_collection_period))
        }

        # Convert interval audit results to a dataframe and add run column
        interval_audit_df = pd.DataFrame(model.audit_list)
        interval_audit_df['run'] = run

        return {
            'patient': patient_results,
            'trial': trial_results,
            'interval_audit': interval_audit_df
        }

    def run_trial(self):
        """
        Execute a single model configuration for multiple runs/replications.

        This is known as a trial, experiment, batch or scenario. These can be
        run sequentially or in parallel.
        """
        # Sequential execution
        if self.param.cores == 1:
            all_results = [self.run_single(run)
                           for run in range(self.param.number_of_runs)]
        # Parallel execution
        else:
            all_results = Parallel(n_jobs=self.param.cores)(
                delayed(self.run_single)(run)
                for run in range(self.param.number_of_runs))

        # Seperate results from each run into appropriate lists
        patient_results_list = [
            result['patient'] for result in all_results]
        trial_results_list = [
            result['trial'] for result in all_results]
        interval_audit_list = [
            result['interval_audit'] for result in all_results]

        # Convert lists into dataframes
        self.patient_results_df = pd.concat(patient_results_list,
                                            ignore_index=True)
        self.trial_results_df = pd.DataFrame(trial_results_list)
        self.interval_audit_df = pd.concat(interval_audit_list,
                                           ignore_index=True)

        # Calculate average results and uncertainty from across all trials
        uncertainty_metrics = {}
        trial_col = self.trial_results_df.columns

        # Loop through the trial-level performance measure columns
        # Calculate mean, standard deviation and 95% confidence interval
        for col in trial_col[~trial_col.isin(['run_number', 'scenario'])]:
            uncertainty_metrics[col] = dict(zip(
                ['mean', 'std_dev', 'lower_95_ci', 'upper_95_ci'],
                summary_stats(self.trial_results_df[col])
            ))
        # Convert to dataframe
        self.overall_results_df = pd.DataFrame(uncertainty_metrics)
