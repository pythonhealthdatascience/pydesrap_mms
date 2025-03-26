# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates formatted as YYYY-MM-DD as per [ISO standard](https://www.iso.org/iso-8601-date-and-time-format.html).

## v1.2.0 - 2025-03-26

Add tests, change from default inputs, rename some variables, and add a method which allows the solution of `ReplicationsAlgorithm` to be less than the `initial_replications` set.

### Added

* Add unit tests for `ReplicationsAlgorithm` when only 2 replications are run, and for the new `find_position()` method.
* Add back test for scenario analysis.

### Changed

* Linting GitHub action no longer triggers on pull requests.
* Renamed `count_unseen` and `q_time_unseen` to be resource-specific (i.e.g `count_unseen_nurse`).
* Set default alpha to 0.05 for `OnlineStatistics`.
* Accept instance of `Param` class as input for `run_scenarios()` rather than a dictionary.

### Fixed

* Add `find_position()` method to `ReplicationsAlgorithm`, allowing us to correct results if the solution was below the `initial_replications` set.

## v1.1.0 - 2025-03-21

Add a bash script for executing notebooks and new tests for warm-up patients and replication consistency. Fixes were made to correct notebook configurations, adjust test parameters, refine the replication algorithm, and ensure accurate calculations, such as correcting nurse time usage and setting appropriate values in the replication algorithm. Other changes include updates to default parameters and documentation.

### Added

* Bash script to execute all notebooks (with `nbconvert` add to environment for this).
* Add test related to inclusion/exclusion of warm-up patients in certain metrics (`test_warmup_high_demand()`).
* Add test for consistent `nreps` between replications methods.

### Changed

* Changed default warm-up length in `Param()`.
* Add pylint line limit so it adheres to PEP-8.
* Allow input of `Param()` to the objects in `replications.py` so we can specify parameter set for back tests (so they don't just change results when we change the model defaults).
* Add specific parameters to `generate_exp_results.ipynb` for back tests.
* Add acknowledgements to README and docstrings.
* Lowered the default `min_rep` for both confidence_interval_method functions.

### Fixed

* Correct `choosing_warmup.ipynb` to use multiple replications and run length at least 5-10x actual.
* Fix `test_waiting_time_utilisation()`
* Correct `test_klimit()` to actually use the parametrize inputs.
* Add correction to `nurse_time_used` for when patients span the warm-up and data collection period.
* Allow `None` for the dashed line in `plotly_confidence_interval_method()`.
* Allow a solution below `initial_replications` in `ReplicationsAlgorithm`.
* Set `target_met` back to 0 in `ReplicationsAlgorithm` if precision is no longer achieved.
* Set `test_consistent_outputs()` to have no lookahead.

## v1.0.0 - 2025-02-27

Lots and lots of changes! Many of these are a result of comments from peer review of code by Tom Monks.

### Added

* Virtual environment alternative to conda.
* Bash script to lint repository.
* Lots of new unit tests and functional tests!
* GitHub actions to run tests and lint repository.
* Add `MonitoredResource` and alternative warm-up results collection.
* Time-weighted statistics - including relevant code (`replications.py`), documentation (`choosing_replications.ipynb`), and tests (`_replications` in tests).
* User-controlled interactive histogram of results in `analysis.ipynb`.
* Add metrics for unseen patients.

### Changed

* Changes to code and environment to accomodate new features (described in 'Added').
* Import simulation as a local package.
* Save all tables and figures.
* Add Tom Monks to author list.
* Expanded README.
* Renaming classes and variables (e.g. `Trial` to `Runner`, `Defaults` to `Param`).
* Improved log formatting.
* Moved methods (e.g. from `analysis.ipynb` to `simulation/`).
* Re-arranged tests into unit tests, back tests and functional tests.

### Fixed

* First arrival no longer at time 0.
* Begin interval audit at start of data collection period (rather than start of warm-up period).
* Correct logging message where wrong time was used.
* Add error handling for invalid cores (in model + test) and error message for attempts to log when in parallel.
* Resolved runtime warning with handling for variance 0 in `summary_stats()`.
* Prevent output of standard deviation or confidence intervals from `summary_stats()` when n<3.
* Add error handling for results processing when there are no arrivals.
* Add error handling for invalid mean in `Exponential`.

## v0.1.0 - 2025-01-09

🌱 First release of the python DES template.