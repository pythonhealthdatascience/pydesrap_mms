"""Simple Reproducible SimPy Discrete-Event Simulation (DES) Model.

Uses object-oriented approach to create an M/M/c model with optional warm-up
period, replications, seed control.

Credit:
    > This code is adapted from Sammi Rosser and Dan Chalk (2024) HSMA - the
    little book of DES (https://github.com/hsma-programme/hsma6_des_book).
    > The distribution classes are adapted from Monks (2021) sim-tools:
    fundamental tools to support the simulation process in python
    (https://github.com/TomMonks/sim-tools).

Typical usage example:

    trial = Trial()
    trial.run_trial()
    print(trial.trial_results_df)
"""

from joblib import Parallel, delayed
import numpy as np
import pandas as pd
import simpy


class Defaults():
    """
    Default parameters for simulation.

    Attributes:
        patient_inter (float):
            Mean inter-arrival time between patients.
        mean_n_consult_time (float):
            Mean nurse consultation time.
        number_of_nurses (int):
            Number of available nurses.
        warm_up_period (int):
            Duration of the warm-up period - running simulation but not yet
            collecting results.
        data_collection_period (int):
            Duration of data collection period (also known as the measurement
            interval) - which begins after any warm-up period
        number_of_runs (int):
            The number of runs (also known as replications), defining how many
            times to re-run the simulation (with different random numbers).
        audit_interval (int):
            How frequently to audit resource utilisation.
        scenario_name (int|float|string):
            Label for the scenario.
    """
    def __init__(self):
        """
        Initalise instance of parameters class.
        """
        # Disable restriction on attribute modification during initialisation
        object.__setattr__(self, '_initialising', True)

        self.patient_inter = 5
        self.mean_n_consult_time = 35
        self.number_of_nurses = 9
        self.warm_up_period = 0
        self.data_collection_period = 600
        self.number_of_runs = 5
        self.audit_interval = 5
        self.scenario_name = 0

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


class Patient:
    """
    Represents a patient.

    Attributes:
        p_id (int):
            Patient's unique identifier.
        q_time_nurse (int):
            Time the patient spent waiting for a nurse.
    """
    def __init__(self, p_id):
        """
        Initialises a new patient.

        Arguments:
            p_id (int):
                Patient's unique identifier.
        """
        self.id = p_id
        self.q_time_nurse = 0


class Exponential:
    """
    Generate samples from an exponential distribution.

    Attributes:
        mean (float):
            Mean of the exponential distribution.
        random_seed (int|None):
            Random seed to reproduce samples. If set to none, then a unique
            sample is created.
        size (int|None):
            Number of samples to return. If set to none, then returns a single
            sample.
    """
    def __init__(self, mean, random_seed=None):
        """
        Initialises a new distribution.

        Arguments:
            mean (float):
                Mean of the exponential distribution.
            random_seed (int|None):
                Random seed to reproduce samples. If set to none, then a unique
                sample is created.
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
        env (simpy.Environment):
            The SimPy environment for the simulation.
        patient_counter (int):
            Counter to create patient IDs.
        nurse (simpy.Resource):
            SimPy resource representing nurses.
        run_number (int):
            Run number for random seed generation.
        nurse_time_used (float):
            Total time the nurse resources have been used.
        results_list (list):
            List to store patient-level results.
        utilisation_audit (list):
            List to store utilisation as recorded at regular intervals.
        patient_inter_arrival_dist (Exponential):
            Distribution for sampling patient inter-arrival times.
        nurse_consult_time_dist (Exponential):
            Distribution for sampling nurse consultation times.
    """
    def __init__(self, param=Defaults(), run_number=0):
        """
        Initalise a new model.

        Arguments:
            param (Defaults, optional):
                Simulation parameters. Defaults to new instance of the
                Defaults() class.
            run_number (int, optional):
                Run number for random seed generation. Defaults to 0.
        """
        self.param = param
        self.env = simpy.Environment()
        self.patient_counter = 0
        self.nurse = simpy.Resource(self.env,
                                    capacity=self.param.number_of_nurses)
        self.run_number = run_number
        self.nurse_time_used = 0
        self.results_list = []
        self.utilisation_audit = []

        # Generate seeds based on run_number as entropy (the "starter" seed)
        # The seeds produced will create independent streams
        ss = np.random.SeedSequence(entropy=self.run_number)
        seeds = ss.spawn(2)

        # Initialise distributions using those seeds
        self.patient_inter_arrival_dist = Exponential(
            mean=self.param.patient_inter, random_seed=seeds[0])
        self.nurse_consult_time_dist = Exponential(
            mean=self.param.mean_n_consult_time, random_seed=seeds[1])

    def generate_patient_arrivals(self):
        """
        Generate patient arrivals.
        """
        while True:
            # Create new patient, with ID based on incremented patient_counter
            self.patient_counter += 1
            p = Patient(self.patient_counter)

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
            end_q_nurse = self.env.now
            patient.q_time_nurse = end_q_nurse - start_q_nurse

            # Sample time spent with nurse
            sampled_nurse_act_time = self.nurse_consult_time_dist.sample()

            # Only save results if the warm-up period has passed
            if self.env.now >= self.param.warm_up_period:
                # Save patient results to results_list
                self.results_list.append({
                    'patient_id': patient.id,
                    'q_time_nurse': patient.q_time_nurse,
                    'time_with_nurse': sampled_nurse_act_time
                })
                # Update total nurse time used - but if consultation would
                # overrun simulation, just use time to simulation end
                remaining_time = (
                    self.param.warm_up_period +
                    self.param.data_collection_period) - self.env.now
                self.nurse_time_used += min(
                    sampled_nurse_act_time, remaining_time)

            # Pass time spent with nurse
            yield self.env.timeout(sampled_nurse_act_time)

    def interval_audit_utilisation(self, resources, interval=1):
        """
        Audit resource utilisation at regular intervals.

        Arguments:
            resource (list of dict):
                List with dictionaries for each resource, in the format:
                [{'name': 'name', 'object': resource}]
            interval (int, optional):
                Time between audits. Defaults to 1.
        """
        while True:
            # Only save results if the warm-up period has passed
            if self.env.now >= self.param.warm_up_period:
                # Collect data for each resource
                for resource in resources:
                    self.utilisation_audit.append({
                        'resource_name': resource['name'],
                        'simulation_time': self.env.now,
                        # Count of resource currently in use
                        'number_utilised': resource['object'].count,
                        # Total number of resource in the simulation
                        'number_available': resource['object'].capacity,
                        # Length of queue for the resource
                        'queue_length': len(resource['object'].queue)
                    })
            # Trigger next audit after desired interval has passed
            yield self.env.timeout(interval)

    def run(self):
        """
        Runs the simulation for the specified duration.
        """
        # Start patient generator
        self.env.process(self.generate_patient_arrivals())

        # Start interval auditor for nurse utilisation
        self.env.process(self.interval_audit_utilisation(
            resources=[{'name': 'nurse', 'object': self.nurse}],
            interval=self.param.audit_interval))

        # Run for specified duration (which is the warm-up period + the
        # data collection period)
        self.env.run(until=self.param.data_collection_period +
                     self.param.warm_up_period)


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
    """
    def __init__(self, param=Defaults()):
        '''
        Initialise a new instance of the trial class.

        Arguments:
            param (Defaults):
                Simulation parameters. Defaults to new instance of the
                Defaults() class.
        '''
        # Store model parameters
        self.param = param
        # Initialise empty dataframes to store results
        self.patient_results_df = pd.DataFrame()
        self.trial_results_df = pd.DataFrame()
        self.interval_audit_df = pd.DataFrame()

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
        my_model = Model(run_number=run)
        my_model.run()

        # Convert patient-level results to a dataframe and add column with run
        patient_results = pd.DataFrame(my_model.results_list)
        patient_results['run'] = run

        # Create dictionary recording the trial-level results
        trial_results = {
            'run_number': run,
            'scenario': self.param.scenario_name,
            'arrivals': len(patient_results),
            'mean_q_time_nurse': patient_results['q_time_nurse'].mean(),
            'average_nurse_utilisation': (my_model.nurse_time_used /
                                          (self.param.number_of_nurses *
                                           self.param.data_collection_period))
        }
        # Convert interval audit results to a dataframe and add columns with
        # the run, and the percentage of resources utilised at a given time
        interval_audit_df = pd.DataFrame(my_model.utilisation_audit)
        interval_audit_df['run'] = run
        interval_audit_df['perc_utilisation'] = (
            interval_audit_df['number_utilised'] /
            interval_audit_df['number_available']
        )
        return {
            'patient': patient_results,
            'trial': trial_results,
            'interval_audit': interval_audit_df
        }

    def run_trial(self, cores=1):
        """
        Execute a single model configuration for multiple runs/replications.

        This is known as a trial, experiment, batch or scenario. These can be
        run sequentially or in parallel.

        Arguments:
            cores (int, optional):
                Number of CPU cores to use for parallel execution. Set to
                desired number, or to -1 to use all available cores. For
                sequential execution, set to 1 (default).
        """
        # Sequential execution
        if cores == 1:
            all_results = [self.run_single(run)
                           for run in range(self.param.number_of_runs)]
        # Parallel execution
        else:
            all_results = Parallel(n_jobs=cores)(
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
