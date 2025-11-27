"""
WarmupAuditor

Acknowledgements
----------------
This approach is adapted from Tom Monks (2024) Lab 6 Output Analysis in
HPDM097 - Making a difference with health data (MIT Licence)
https://github.com/health-data-science-OR/stochastic_systems.
"""

import numpy as np


class WarmupAuditor():
    """
    Warm-up auditor for the model.
    Records cumulative mean results at regular intervals.

    Attributes
    ----------
    model : Model
        Instance of Model() to run the simulation.
    interval : int
        Audit frequency (minutes).
    audit_results : list
        List of dictionaries containing audit snapshots at each interval.
    current_time : int
        Current simulation time to perform audit.
    """
    def __init__(self, model, interval):
        """
        Initialise auditor.

        Parameters
        ----------
        model : Model
            Instance of Model() to run the simulation.
        interval : int
            Audit frequency (minutes).
        """
        self.model = model
        self.interval = interval
        self.audit_results = []
        self.current_time = np.nan

    def run(self):
        """
        Run auditor alongside simulation model.
        """
        self.model.env.process(self._audit_model())
        self.model.run()

    def _audit_model(self):
        """
        Audit the model at the specified intervals.
        """
        while True:
            self.current_time = self.model.env.now
            self.audit_results.append({
                "time": self.current_time,
                "wait_time": self._get_wait_time(),
                "time_in_system": self._get_time_in_system(),
                "queue_length": self._get_queue_length(),
                "utilisation": self._get_utilisation(),
                "patients_in_system": self._get_patients_in_system()
            })
            yield self.model.env.timeout(self.interval)

    def _get_wait_time(self):
        """
        Compute mean wait time for patients seen by current time.

        Returns
        -------
        float
            Mean wait time across all patients who have been seen.
        """
        wait_times = [
            patient.q_time_nurse
            for patient in self.model.patients
            if not np.isnan(patient.q_time_nurse)
        ]
        if wait_times:
            return np.mean(wait_times)
        return np.nan

    def _get_time_in_system(self):
        """
        Compute mean time in system (for patients completed by current time).

        Returns
        -------
        float
            Mean time in system for patients completed by current time.
        """
        time_in_system = []
        for patient in self.model.patients:
            if not np.isnan(patient.end_time):
                time_in_system.append(patient.end_time - patient.arrival_time)
        if time_in_system:
            return np.mean(time_in_system)
        return np.nan

    def _get_queue_length(self):
        """
        Compute time-weighted mean queue length up to current time.

        Returns
        -------
        float
            Time-weighted mean queue length from start to current time.
        """
        total_area = sum(self.model.nurse.area_n_in_queue)
        if self.current_time > 0:
            return total_area / self.current_time
        return 0

    def _get_utilisation(self):
        """
        Compute time-weighted mean utilisation up to current time.

        Returns
        -------
        float
            Time-weighted mean utilisation from start to current time.
        """
        total_area = sum(self.model.nurse.area_resource_busy)
        total_capacity = self.model.param.number_of_nurses * self.current_time
        if self.current_time > 0:
            return total_area / total_capacity
        return 0

    def _get_patients_in_system(self):
        """
        Computer time-weighted mean patients in system up to current time.

        Returns
        -------
        float
            Time-weighted mean patients in system from start to current time.
        """
        total_area = sum(self.model.area_n_in_system)
        if self.current_time > 0:
            return total_area / self.current_time
        return 0
