"""
Param.
"""

from simulation import SimLogger


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
        Initialise instance of parameters class.

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
                sequential execution, set to 1.
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
