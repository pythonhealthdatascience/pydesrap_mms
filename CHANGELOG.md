# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Dates formatted as YYYY-MM-DD as per [ISO standard](https://www.iso.org/iso-8601-date-and-time-format.html).

## v1.0.0 - 2025-01-27

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