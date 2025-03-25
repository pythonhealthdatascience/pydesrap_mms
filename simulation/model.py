"""Simple Reproducible SimPy Discrete-Event Simulation (DES) Model.

Uses object-oriented approach to create an M/M/c model with a warm-up
period, replications, seed control. For this example application, the time unit
is described as minutes, but this could be changed - for example, to hours,
days.

Credit:
    > This code is adapted from Sammi Rosser and Dan Chalk (2024) HSMA - the
    little book of DES (https://github.com/hsma-programme/hsma6_des_book)
    (MIT Licence).
    > The Exponential class is based on Tom Monks (2021) sim-tools:
    fundamental tools to support the simulation process in python
    (https://github.com/TomMonks/sim-tools) (MIT Licence). For other
    distributions (bernoulli, lognormal, normal, uniform, triangular, fixed,
    combination, continuous empirical, erlang, weibull, gamma, beta, discrete,
    truncated, raw empirical, pearsonV, pearsonVI, erlangK, poisson), check
    out the sim-tools package.
    > The MonitoredResource class is based on Tom Monks, Alison Harper and Amy
    Heather (2025) An introduction to Discrete-Event Simulation (DES) using
    Free and Open Source Software
    (https://github.com/pythonhealthdatascience/intro-open-sim/tree/main)
    (MIT Licence). They based it on the method described in Law. Simulation
    Modeling and Analysis 4th Ed. Pages 14 - 17.

Licence:
    This project is licensed under the MIT Licence. See the LICENSE file for
    more details.

Typical usage example:
    experiment = Runner(param=Param())
    experiment.run_reps()
    print(experiment.run_results_df)
"""

import itertools

from joblib import Parallel, delayed, cpu_count
import numpy as np
import pandas as pd
import simpy

from simulation.logging import SimLogger
from simulation.helper import summary_stats


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class Param:
    """
    Default parameters for simulation.

    Attributes are described in initialisation docstring.
    """
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        patient_inter=4,
        mean_n_consult_time=10,
        number_of_nurses=5,
        warm_up_period=1440*27,  # 27 days
        data_collection_period=1440*30,  # 30 days
        number_of_runs=31,
        audit_interval=120,  # every 2 hours
        scenario_name=0,
        cores=-1,
        logger=SimLogger(log_to_console=False, log_to_file=False)
    ):
        """
        Initalise instance of parameters class.

        Arguments:
            patient_inter (float):
                Mean inter-arrival time between patients in minutes.
            mean_n_consult_time (float):
                Mean nurse consultation time in minutes.
            number_of_nurses (float):
                Number of available nurses.
            warm_up_period (int):
                Duration of the warm-up period in minutes - running simulation
                but not yet collecting results.
            data_collection_period (int):
                Duration of data collection period in minutes (also known as
                measurement interval) - which begins after any warm-up period.
            number_of_runs (int):
                The number of runs (i.e. replications), defining how many
                times to re-run the simulation (with different random numbers).
            audit_interval (int):
                How frequently to audit resource utilisation, in minutes.
            scenario_name (int|float|string):
                Label for the scenario.
            cores (int):
                Number of CPU cores to use for parallel execution. Set to
                desired number, or to -1 to use all available cores. For
                sequential execution, set to 1 (default).
            logger (logging.Logger):
                The logging instance used for logging messages.
        """
        # Disable restriction on attribute modification during initialisation
        object.__setattr__(self, '_initialising', True)

        self.patient_inter = patient_inter
        self.mean_n_consult_time = mean_n_consult_time
        self.number_of_nurses = number_of_nurses
        self.warm_up_period = warm_up_period
        self.data_collection_period = data_collection_period
        self.number_of_runs = number_of_runs
        self.audit_interval = audit_interval
        self.scenario_name = scenario_name
        self.cores = cores
        self.logger = logger

        # Re-enable attribute checks after initialisation
        object.__setattr__(self, '_initialising', False)

    def __setattr__(self, name, value):
        """
        Prevent addition of new attributes.

        This method overrides the default `__setattr__` behavior to restrict
        the addition of new attributes to the instance. It allows modification
        of existing attributes but raises an `AttributeError` if an attempt is
        made to create a new attribute. This ensures that accidental typos in
        attribute names do not silently create new attributes.

        Arguments:
            name (str):
                The name of the attribute to set.
            value (Any):
                The value to assign to the attribute.

        Raises:
            AttributeError:
                If `name` is not an existing attribute and an attempt is made
                to add it to the instance.
        """
        # Skip the check if the object is still initialising
        # pylint: disable=maybe-no-member
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
        patient_id (int|float|string):
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


class MonitoredResource(simpy.Resource):
    """
    Subclass of simpy.Resource used to monitor resource usage during the run.

    Calculates resource utilisation and the queue length during the model run.
    As it is a subclass, it inherits the attributes and methods from
    simpy.Resource, which is referred to as the superclass or parent class.

    Attributes:
        time_last_event (list):
            Time of last resource request or release.
        area_n_in_queue (list):
            Time that patients have spent queueing for the resource
            (i.e. sum of the times each patient spent waiting). Used to
            calculate the average queue length.
        area_resource_busy (list):
            Time that resources have been in use during the simulation
            (i.e. sum of the times each individual resource was busy). Used
            to calculated utilisation.

    Acknowledgements:
        - Class adapted from Monks, Harper and Heather 2025.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialises a MonitoredResource - which involves initialising a SimPy
        resource and resetting monitoring attributes.

        Arguments:
            *args:
                Positional arguments to be passed to the parent class.
            **kwargs:
                Keyword arguments to be passed to the parent class.
        """
        # Initialise a SimPy Resource
        super().__init__(*args, **kwargs)
        # Run the init_results() method
        self.init_results()

    def init_results(self):
        """
        Resets monitoring attributes to initial values.
        """
        self.time_last_event = [self._env.now]
        self.area_n_in_queue = [0.0]
        self.area_resource_busy = [0.0]

    def request(self, *args, **kwargs):
        """
        Requests a resource, but updates time-weighted statistics BEFORE
        making the request.

        Arguments:
            *args:
                Positional arguments to be passed to the parent class.
            **kwargs:
                Keyword arguments to be passed to the parent class.

        Returns:
            simpy.events.Event:
                Event representing the request.
        """
        # Update time-weighted statistics
        self.update_time_weighted_stats()
        # Request a resource
        return super().request(*args, **kwargs)

    def release(self, *args, **kwargs):
        """
        Releases a resource, but updates time-weighted statistics BEFORE
        releasing it.

        Arguments:
            *args:
                Positional arguments to be passed to the parent class.
            **kwargs:
                Keyword arguments to be passed to the parent class.#

        Returns:
            simpy.events.Event:
                Event representing the request.
        """
        # Update time-weighted statistics
        self.update_time_weighted_stats()
        # Release a resource
        return super().release(*args, **kwargs)

    def update_time_weighted_stats(self):
        """
        Update the time-weighted statistics for resource usage.

        Between every request or release of the resource, it calculates the
        relevant statistics - e.g.:
        - Total queue time (number of requests in queue * time)
        - Total resource use (number of resources in use * time)
        These are summed to return the totals from across the whole simulation.
        In Runner.run_single(), these are then used to calculate utilisation.

        Further details:
        - These sums can be referred to as "the area under the curve".
        - They are called "time-weighted" statistics as they account for how
        long certain events or states (such as resource use or queue length)
        persist over time.
        """
        # Calculate time since last event
        time_since_last_event = self._env.now - self.time_last_event[-1]

        # Add record of current time
        self.time_last_event.append(self._env.now)

        # Add "area under curve" of people in queue
        # len(self.queue) is the number of requests queued
        self.area_n_in_queue.append(len(self.queue) * time_since_last_event)

        # Add "area under curve" of resources in use
        # self.count is the number of resources in use
        self.area_resource_busy.append(self.count * time_since_last_event)


class Exponential:
    """
    Generate samples from an exponential distribution.

    Attributes:
        mean (float):
            Mean of the exponential distribution.
        rand (numpy.random.Generator):
            Random number generator for producing samples.

    Acknowledgement:
        - Class adapted from Monks 2021.
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
        if mean <= 0:
            raise ValueError('Exponential mean must be greater than 0.')

        self.mean = mean
        self.rand = np.random.default_rng(random_seed)

    def sample(self, size=None):
        """
        Generate sample.

        Arguments:
            size (int|None):
                Number of samples to return. If set to none, then returns a
                single sample.

        Returns:
            float or numpy.ndarray:
                A single sample if size is None, or an array of samples if
                size is specified.
        """
        return self.rand.exponential(self.mean, size=size)


class Model:
    """
    Simulation model for a clinic.

    In this model, patients arrive at the clinic, wait for an available
    nurse, have a consultation with the nurse, and then leave.

    Attributes:
        param (Param):
            Simulation parameters.
        run_number (int):
            Run number for random seed generation.
        env (simpy.Environment):
            The SimPy environment for the simulation.
        nurse (MonitoredResource):
            Subclass of SimPy resource representing nurses (whilst monitoring
            the resource during the simulation run).
        patients (list):
            List containing the generated patient objects.
        nurse_time_used (float):
            Total time the nurse resources have been used in minutes.
        nurse_time_used_correction (float):
            Correction for nurse time used with a warm-up period. Without
            correction, it will be underestimated, as patients who start their
            time with the nurse during the warm-up period and finish it during
            the data collection period will not be included in the recorded
            time.
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

    Acknowledgements:
        - Class adapted from Rosser and Chalk 2024.
    """
    def __init__(self, param, run_number):
        """
        Initalise a new model.

        Arguments:
            param (Param, optional):
                Simulation parameters. Defaults to new instance of the
                Param() class.
            run_number (int):
                Run number for random seed generation.
        """
        # Set parameters and run number
        self.param = param
        self.run_number = run_number

        # Check validity of provided parameters
        self.valid_inputs()

        # Create simpy environment and resource
        self.env = simpy.Environment()
        self.nurse = MonitoredResource(self.env,
                                       capacity=self.param.number_of_nurses)

        # Initialise attributes to store results
        self.patients = []
        self.nurse_time_used = 0
        self.nurse_time_used_correction = 0
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

        # Log model initialisation
        self.param.logger.log(sim_time=self.env.now, msg='Initialise model:\n')
        self.param.logger.log(vars(self))
        self.param.logger.log(sim_time=self.env.now, msg='Parameters:\n ')
        self.param.logger.log(vars(self.param))

    def valid_inputs(self):
        """
        Checks validity of provided parameters.
        """
        # Define validation rules for attributes
        # Doesn't include number_of_nurses as this is tested by simpy.Resource
        validation_rules = {
            'positive': ['patient_inter', 'mean_n_consult_time',
                         'number_of_runs', 'audit_interval',
                         'number_of_nurses'],
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
                if rule == 'non_negative' and param_value < 0:
                    raise ValueError(
                        f'Parameter "{param_name}" must be greater than or ' +
                        'equal to 0.'
                    )

    def generate_patient_arrivals(self):
        """
        Generate patient arrivals.
        """
        while True:
            # Sample and pass time to arrival
            sampled_inter = self.patient_inter_arrival_dist.sample()
            yield self.env.timeout(sampled_inter)

            # Create new patient, with ID based on length of patient list + 1
            p = Patient(len(self.patients) + 1)
            p.arrival_time = self.env.now

            # Add the patient to the list.
            # The list stores a reference to the patient object, so any updates
            # to the patient attributes will be reflected in the list as well
            self.patients.append(p)

            # Log arrival time
            if p.arrival_time < self.param.warm_up_period:
                arrive_pre = '\U0001F538 WU'
            else:
                arrive_pre = '\U0001F539 DC'
            self.param.logger.log(
                sim_time=self.env.now,
                msg=(f'{arrive_pre} Patient {p.patient_id} arrives at: ' +
                     f'{p.arrival_time:.3f}.')
            )

            # Start process of attending clinic
            self.env.process(self.attend_clinic(p))

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

            # Log wait time and time spent with nurse
            if patient.arrival_time < self.param.warm_up_period:
                nurse_pre = '\U0001F536 WU'
            else:
                nurse_pre = '\U0001F537 DC'
            self.param.logger.log(
                sim_time=self.env.now,
                msg=(f'{nurse_pre} Patient {patient.patient_id} is seen ' +
                     f'by nurse after {patient.q_time_nurse:.3f}. ' +
                     f'Consultation length: {patient.time_with_nurse:.3f}.')
            )

            # Update the total nurse time used.
            # This is used to calculate utilisation. To avoid overestimation,
            # if the consultation would overrun the simulation, just record
            # time to end of the simulation.
            remaining_time = (
                self.param.warm_up_period +
                self.param.data_collection_period) - self.env.now
            self.nurse_time_used += min(
                patient.time_with_nurse, remaining_time)

            # If still in the warm-up period, find if the patient time with
            # nurse will go beyond end (if time_exceeding_warmup is positive) -
            # and, in which case, save that to nurse_time_used_correction
            # (ensuring to correct it if would exceed end of simulation).
            remaining_warmup = self.param.warm_up_period - self.env.now
            if remaining_warmup > 0:
                time_exceeding_warmup = (patient.time_with_nurse -
                                         remaining_warmup)
                if time_exceeding_warmup > 0:
                    self.nurse_time_used_correction += min(
                        time_exceeding_warmup,
                        self.param.data_collection_period)
                    # Logging message
                    self.param.logger.log(
                        sim_time=self.env.now,
                        msg=(f'\U0001F6E0 Patient {patient.patient_id} ' +
                             'starts consultation with ' +
                             f'{remaining_warmup:.3f} left of warm-up (which' +
                             f' is {self.param.warm_up_period:.3f}). As ' +
                             'their consultation is for ' +
                             f'{patient.time_with_nurse:.3f}, they will ' +
                             f'exceed warmup by {time_exceeding_warmup:.3f},' +
                             ' so we correct for this.')
                    )

            # Pass time spent with nurse
            yield self.env.timeout(patient.time_with_nurse)

    def interval_audit(self, interval):
        """
        Audit waiting times and resource utilisation at regular intervals.
        This is set-up to start when the warm-up period has ended.

        The running mean wait time is calculated using Welford's Running
        Average, which is a method that avoids the need to store previous wait
        times to compute the average. The running mean reflects the main wait
        time for all patients seen by nurse up to that point in the simulation.

        Arguments:
            interval (int, optional):
                Time between audits in minutes.
        """
        # Wait until warm-up period has passed
        yield self.env.timeout(self.param.warm_up_period)

        # Begin interval auditor
        while True:
            self.audit_list.append({
                'resource_name': 'nurse',
                'simulation_time': self.env.now,
                'utilisation': self.nurse.count / self.nurse.capacity,
                'queue_length': len(self.nurse.queue),
                'running_mean_wait_time': self.running_mean_nurse_wait
            })

            # Trigger next audit after desired interval has passed
            yield self.env.timeout(interval)

    def init_results_variables(self):
        """
        Resets all results collection variables to their initial values.
        """
        self.patients = []
        self.nurse_time_used = 0
        self.audit_list = []
        self.nurse.init_results()

    def warm_up_complete(self):
        """
        If there is a warm-up period, then reset all results collection
        variables once warm-up period has passed.
        """
        if self.param.warm_up_period > 0:
            # Delay process until warm-up period has completed
            yield self.env.timeout(self.param.warm_up_period)

            # Reset results collection variables
            self.init_results_variables()

            # Correct nurse_time_used, adding the remaining time of patients
            # who were partway through their consultation during the warm-up
            # period (i.e. patients still in consultation as enter the
            # data collection period).
            self.nurse_time_used += self.nurse_time_used_correction

            # If there was a warm-up period, log that this time has passed so
            # can distinguish between patients before and after warm-up in logs
            if self.param.warm_up_period > 0:
                self.param.logger.log(sim_time=self.env.now,
                                      msg='─' * 10)
                self.param.logger.log(sim_time=self.env.now,
                                      msg='Warm up complete.')
                self.param.logger.log(sim_time=self.env.now,
                                      msg='─' * 10)

    def run(self):
        """
        Runs the simulation for the specified duration.
        """
        # Calculate the total run length
        run_length = (self.param.warm_up_period +
                      self.param.data_collection_period)

        # Schedule process which will reset results when warm-up period ends
        # (or does nothing if there is no warm-up)
        self.env.process(self.warm_up_complete())

        # Schedule patient generator to run during simulation
        self.env.process(self.generate_patient_arrivals())

        # Schedule interval auditor to run during simulation
        self.env.process(
            self.interval_audit(interval=self.param.audit_interval))

        # Run the simulation
        self.env.run(until=run_length)

        # If the simulation ends while resources are still in use or requests
        # are still in the queue, the time between the last recorded event and
        # the simulation end will not have been accounted for. Hence, we call
        # update_time_weighted_stats() to run for last event --> end.
        self.nurse.update_time_weighted_stats()

        # Error handling - if there was no data collection period, the
        # simulation ends before it has a chance to reset the results,
        # so we do so manually
        if self.param.data_collection_period == 0:
            self.init_results_variables()

        # Convert list of patient objects into a list that just contains the
        # attributes of each of those patients as dictionaries
        self.results_list = [x.__dict__ for x in self.patients]


class Runner:
    """
    Run the simulation.

    Manages simulation runs, either running the model once or multiple times
    (replications).

    Attributes:
        param (Param):
            Simulation parameters.
        patient_results_df (pandas.DataFrame):
            Dataframe to store patient-level results.
        run_results_df (pandas.DataFrame):
            Dataframe to store results from each run.
        interval_audit_df (pandas.DataFrame):
            Dataframe to store interval audit results.
        overall_results_df (pandas.DataFrame):
            Dataframe to store average results from across the runs.

    Acknowledgements:
        - Class adapted from Rosser and Chalk 2024.
    """
    def __init__(self, param):
        '''
        Initialise a new instance of the Runner class.

        Arguments:
            param (Param):
                Simulation parameters.
        '''
        # Store model parameters
        self.param = param
        # Initialise empty dataframes to store results
        self.patient_results_df = pd.DataFrame()
        self.run_results_df = pd.DataFrame()
        self.interval_audit_df = pd.DataFrame()
        self.overall_results_df = pd.DataFrame()

    def run_single(self, run):
        """
        Executes a single simulation run and records the results.

        Arguments:
            run (int):
                The run number for the simulation.

        Returns:
            dict:
                A dictionary containing the patient-level results, results
                from each run, and interval audit results.
        """
        # Run model
        model = Model(param=self.param, run_number=run)
        model.run()

        # PATIENT RESULTS
        # Convert patient-level results to a dataframe and add column with run
        patient_results = pd.DataFrame(model.results_list)
        patient_results['run'] = run
        # If there was at least one patient...
        if len(patient_results) > 0:
            # Add a column with the wait time of patients who remained unseen
            # at the end of the simulation
            patient_results['q_time_unseen_nurse'] = np.where(
                patient_results['time_with_nurse'].isna(),
                model.env.now - patient_results['arrival_time'], np.nan
            )
        else:
            # Set to NaN if no patients
            patient_results['q_time_unseen_nurse'] = np.nan

        # RUN RESULTS
        # The run, scenario and arrivals are handled the same regardless of
        # whether there were any patients
        run_results = {
            'run_number': run,
            'scenario': self.param.scenario_name,
            'arrivals': len(patient_results)
        }
        # If there was at least one patient...
        if len(patient_results) > 0:
            # Create dictionary recording the run results
            # Currently has two alternative methods of measuring utilisation
            run_results = {
                **run_results,
                'mean_q_time_nurse': patient_results['q_time_nurse'].mean(),
                'mean_time_with_nurse': (
                    patient_results['time_with_nurse'].mean()),
                'mean_nurse_utilisation': (
                    model.nurse_time_used / (
                        self.param.number_of_nurses *
                        self.param.data_collection_period)),
                'mean_nurse_utilisation_tw': (
                    sum(model.nurse.area_resource_busy) / (
                        self.param.number_of_nurses *
                        self.param.data_collection_period)),
                'mean_nurse_q_length': (sum(model.nurse.area_n_in_queue) /
                                        self.param.data_collection_period),
                'count_nurse_unseen': (
                    patient_results['time_with_nurse'].isna().sum()),
                'mean_q_time_nurse_unseen': (
                    patient_results['q_time_unseen_nurse'].mean())
            }
        else:
            # Set results to NaN if no patients
            run_results = {
                **run_results,
                'mean_q_time_nurse': np.nan,
                'mean_time_with_nurse': np.nan,
                'mean_nurse_utilisation': np.nan,
                'mean_nurse_utilisation_tw': np.nan,
                'mean_nurse_q_length': np.nan,
                'count_nurse_unseen': np.nan,
                'mean_q_time_nurse_unseen': np.nan
            }

        # INTERVAL AUDIT RESULTS
        # Convert interval audit results to a dataframe and add run column
        interval_audit_df = pd.DataFrame(model.audit_list)
        interval_audit_df['run'] = run

        return {
            'patient': patient_results,
            'run': run_results,
            'interval_audit': interval_audit_df
        }

    def run_reps(self):
        """
        Execute a single model configuration for multiple runs/replications.

        These can be run sequentially or in parallel.
        """
        # Sequential execution
        if self.param.cores == 1:
            all_results = [self.run_single(run)
                           for run in range(self.param.number_of_runs)]
        # Parallel execution
        else:

            # Check number of cores is valid - must be -1, or between 1 and
            # total CPUs-1 (saving one for logic control).
            # Done here rather than in model as this is called before model,
            # and only relevant for Runner.
            valid_cores = [-1] + list(range(1, cpu_count()))
            if self.param.cores not in valid_cores:
                raise ValueError(
                    f'Invalid cores: {self.param.cores}. Must be one of: ' +
                    f'{valid_cores}.')

            # Warn users that logging will not run as it is in parallel
            if (
                self.param.logger.log_to_console or
                self.param.logger.log_to_file
            ):
                self.param.logger.log(
                    'WARNING: Logging is disabled in parallel ' +
                    '(multiprocessing mode). Simulation log will not appear.' +
                    ' If you wish to generate logs, switch to `cores=1`, or ' +
                    'just run one replication with `run_single()`.')

            # Execute replications
            all_results = Parallel(n_jobs=self.param.cores)(
                delayed(self.run_single)(run)
                for run in range(self.param.number_of_runs))

        # Seperate results from each run into appropriate lists
        patient_results_list = [
            result['patient'] for result in all_results]
        run_results_list = [
            result['run'] for result in all_results]
        interval_audit_list = [
            result['interval_audit'] for result in all_results]

        # Convert lists into dataframes
        self.patient_results_df = pd.concat(patient_results_list,
                                            ignore_index=True)
        self.run_results_df = pd.DataFrame(run_results_list)
        self.interval_audit_df = pd.concat(interval_audit_list,
                                           ignore_index=True)

        # Calculate average results and uncertainty from across all runs
        uncertainty_metrics = {}
        run_col = self.run_results_df.columns

        # Loop through the run performance measure columns
        # Calculate mean, standard deviation and 95% confidence interval
        for col in run_col[~run_col.isin(['run_number', 'scenario'])]:
            uncertainty_metrics[col] = dict(zip(
                ['mean', 'std_dev', 'lower_95_ci', 'upper_95_ci'],
                summary_stats(self.run_results_df[col])
            ))
        # Convert to dataframe
        self.overall_results_df = pd.DataFrame(uncertainty_metrics)


def run_scenarios(scenarios, param=None):
    """
    Execute a set of scenarios and return the results from each run.

    Arguments:
        scenarios (dict):
            Dictionary where key is name of parameter and value is a list
            with different values to run in scenarios.
        param (dict):
            Instance of Param with parameters for the base case. Optional,
            defaults to use those as set in Param.

    Returns:
        pandas.dataframe:
            Dataframe with results from each run of each scenario.

    Acknowledgements:
        - Function adapted from Rosser and Chalk 2024.
    """
    # Find every possible permutation of the scenarios
    all_scenarios_tuples = list(itertools.product(*scenarios.values()))
    # Convert back into dictionaries
    all_scenarios_dicts = [
        dict(zip(scenarios.keys(), p)) for p in all_scenarios_tuples]
    # Preview some of the scenarios
    print(f'There are {len(all_scenarios_dicts)} scenarios. Running:')

    # Run the scenarios...
    results = []
    for index, scenario_to_run in enumerate(all_scenarios_dicts):
        print(scenario_to_run)

        # Create instance of parameter class, if not provided
        if param is None:
            param = Param()

        # Update parameter list with the scenario parameters
        param.scenario_name = index
        for key in scenario_to_run:
            setattr(param, key, scenario_to_run[key])

        # Perform replications and keep results from each run, adding the
        # scenario values to the results dataframe
        scenario_exp = Runner(param)
        scenario_exp.run_reps()
        for key in scenario_to_run:
            scenario_exp.run_results_df[key] = scenario_to_run[key]
        results.append(scenario_exp.run_results_df)
    return pd.concat(results)
