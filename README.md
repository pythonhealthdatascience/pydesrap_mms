<div align="center">

# Simple M/M/s queuing model: Python DES RAP

[![python](https://img.shields.io/badge/-Python_3.13-306998?logo=python&logoColor=white)](https://www.python.org/)
[![licence](https://img.shields.io/badge/Licence-MIT-green.svg?labelColor=gray)](https://github.com/pythonhealthdatascience/pydesrap_mms/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14622466.svg)](https://doi.org/10.5281/zenodo.14622466)
[![Tests](https://github.com/pythonhealthdatascience/pydesrap_mms/actions/workflows/tests.yaml/badge.svg)](https://github.com/pythonhealthdatascience/pydesrap_mms/actions/workflows/tests.yaml)
[![Linting](https://github.com/pythonhealthdatascience/pydesrap_mms/actions/workflows/lint.yaml/badge.svg)](https://github.com/pythonhealthdatascience/pydesrap_mms/actions/workflows/lint.yaml)
[![Coverage](https://github.com/pythonhealthdatascience/pydesrap_mms/raw/main/images/coverage-badge.svg)](https://github.com/pythonhealthdatascience/pydesrap_mms/actions/workflows/tests.yaml)
</div>

<br>

This repository is an example accompanying the [**DES RAP Book**](https://github.com/pythonhealthdatascience/des_rap_book) — an open educational resource on reproducible discrete-event simulation (DES) in Python and R. The book demonstrates best practices for building, validating, and sharing DES models within a reproducible analytical pipeline (RAP). The `pydesrap_mms` model illustrates how these principles can be applied to a simple queueing model.

<br>

## Repository overview

This repository provides a reproducible analytical pipeline (RAP) for a simple **M/M/s queuing model** implemented in Python using SimPy. The model simulates patients arriving, waiting to see a nurse, being served, and leaving. All code is structured as a local Python package.

![](images/nurse_des.drawio.png)

An M/M/s queueing model is a classic mathematical model for systems where:

* Arrivals happen at random, following a Poisson process - and the time between arrivals follows an exponential distribution (the first "M", which stands for "Markovian" as it is memoryless - arrivals are independent).
* Service times are exponential (second "M").
* There are s parallel servers (e.g. nurses) sharing a single queue.

This type of model is widely used for studying waiting lines in healthcare, call centers, and other service systems. It helps answer questions like: How long will people wait? How many servers are needed to keep waits short? The only required inputs are the average arrival rate, average service time, and the number of servers.

<br>

## Usage and reproduction instructions

<details><summary><b>Installation</b></summary>

Clone the repository:

```
git clone https://github.com/pythonhealthdatascience/pydesrap_mms.git
cd pydesrap_mms
```

Set up the Python environment using `conda` (recommended):

```
conda env create --file environment.yaml
conda activate
```

There is also a `requirements.txt` file which can be used to set up the environment with `virtualenv`, but this won't fetch a specific version of Python - so please note the version listed in `environment.yaml`.

</details>

<br>

<details><summary><b>How to run</b></summary>

The simulation code is in the `simulation/` folder as a local package. Example analyses and model runs are in `notebooks/`.

**Load the local package:**

```{.r}
%load_ext autoreload
%autoreload 1
%aimport simulation

from simulation import Param, Runner, run_scenarios, summary_stats
# etc.
```

**Run a single simulation:**

```{.r}
param = Param()
experiment = Runner(param)
experiment.run_single()
```

**Run multiple replications:**

```{.r}
param = Param()
experiment = Runner(param)
experiment.run_reps()
```

**Run all example analyses (from command line):**

```{.bash}
bash run_notebooks.sh
```

To run one notebook from the command line (with the same settings - clearing the meta data etc):

```{.bash}
bash run_notebooks.sh notebooks/notebook_name.ipynb
```


</details>

<br>

<details><summary><b>Input data</b></summary>

**Patient-level data** for our system is provided in the file: `inputs/NHS_synthetic.csv`.

**Data dictionary** (explaining each field) is available in: `inputs/NHS_synthetic_dictionary.csv`.

This dataset is **synthetic** and was generated in the `inputs/generator_scripts/synthetic_data_generation.ipynb`based on the the structure of some fields from the [Emergency Care Data Set (ECDS)](https://digital.nhs.uk/data-and-information/data-collections-and-data-sets/data-sets/emergency-care-data-set-ecds). The data generation process involved:

* **Arrivals:** Sampled from a Poisson distribution (average 15 patients per hour).
* **Wait times:** Sampled from an exponential distribution (average wait time: 5 minutes).
* **Service times:** Sampled from an exponential distribution (average service time: 10 minutes).
* **Time period:** Data covers one full year (1st January - 31st December 2025).

This dataset is released under the MIT licence. If you use this data, please cite this repository.

The code for input modelling is in: `notebooks/input_modelling.ipynb`. Model parameters are determined in this file and then stored in: `simulation/model.py`. Description for each parameter can be found in the class docstring within this file.

</details>

<br>

<details><summary><b>Reproducing results</b></summary>

To generate the figures and tables from the paper (`mock_paper.md`), execute:

* **Figures 1-4**: `notebooks/analysis.ipynb`
* **Figures A.1-A.2**: `notebooks/input_modelling.ipynb`
* **Figure B.1**: `notebooks/choosing_warmup.ipynb`
* **Figures C.1-C.3**: `notebooks/choosing_replications.ipynb`

</details>

<br>

<details><summary><b>Run time and machine specification</b></summary>

Run times from our analyses (on Intel Core i7-12700H, 32GB RAM, Ubuntu 24.04.1):

* `analysis.ipynb` - 35s
* `choosing_cores.ipynb` - 34s
* `choosing_replications.ipynb` - 46s
* `choosing_warmup.ipynb` - 38s
* `generate_exp_results.ipynb` - 1s
* `logs.ipynb` - 0s
* `time_weighted_averages.ipynb` - 2s

</details>

<br>

## Project details and credits

### How to cite the repository

If you use this repository, please cite either the GitHub repository or Zenodo:

> Heather, A. Monks, T. (2025). Simple M/M/s queuing model: Python DES RAP. GitHub. https://github.com/pythonhealthdatascience/pydesrap_mms.
>
> Heather, A. Monks, T. (2025). Simple M/M/s queuing model: Python DES RAP. Zenodo. https://doi.org/10.5281/zenodo.14622466

### Contributors

**Amy Heather** - developed the repository.

* [![ORCID](https://img.shields.io/badge/ORCID-0000--0002--6596--3479-A6CE39?style=for-the-badge&logo=orcid&logoColor=white)](https://orcid.org/0000-0002-6596-3479)
* [![GitHub](https://img.shields.io/badge/GitHub-amyheather-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/amyheather)

**Tom Monks** - peer review of the repository.

* [![ORCID](https://img.shields.io/badge/ORCID-0000--0003--2631--4481-A6CE39?style=for-the-badge&logo=orcid&logoColor=white)](https://orcid.org/0000-0003-2631-4481)
* [![GitHub](https://img.shields.io/badge/GitHub-TomMonks-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/TomMonks)

### Licence

MIT Licence. See `LICENSE` for details.

### Community

Curious about contributing? Check out the [contributing guidelines](CONTRIBUTING.md) to learn how you can help. Every bit of help counts, and your contribution - no matter how minor - is highly valued.

### Acknowledgements

This repository was developed with thanks to several others sources. These are acknowledged throughout in the relevant notebooks/modules/functions, and also summarised here:

| Source | Find out more about how it was used... |
| - | - |
| Amy Heather, Thomas Monks, Alison Harper, Navonil Mustafee, Andrew Mayne (2025) On the reproducibility of discrete-event simulation studies in health research: an empirical study using open models (https://doi.org/10.48550/arXiv.2501.13137). | `docs/heather_2025.md` |
| NHS Digital (2024) RAP repository template (https://github.com/NHSDigital/rap-package-template) (MIT Licence) | `simulation/logging.py`<br>`docs/nhs_rap.md` |
| Sammi Rosser and Dan Chalk (2024) HSMA - the little book of DES (https://github.com/hsma-programme/hsma6_des_book) (MIT Licence) | `simulation/model.py`<br>`simulation/patient.py`<br>`simulation/runner.py`<br>`notebooks/choosing_cores.ipynb` |
| Tom Monks (2025) sim-tools: tools to support the Discrete-Event Simulation process in python (https://github.com/TomMonks/sim-tools) (MIT Licence)<br>Who themselves cite Hoad, Robinson, & Davies (2010). Automated selection of the number of replications for a discrete-event simulation (https://www.jstor.org/stable/40926090), and Knuth. D "The Art of Computer Programming" Vol 2. 2nd ed. Page 216. | `simulation/confidence_interval_method.py`<br>`simulation/onlinestatistics.py`<br>`simulation/plotly_confidence_interval_method.py`<br>`simulation/replicationsalgorithm.py`<br>`simulation/replicationtabulizer.py`<br>`notebooks/choosing_replications.ipynb` |
| Tom Monks, Alison Harper and Amy Heather (2025) An introduction to Discrete-Event Simulation (DES) using Free and Open Source Software (https://github.com/pythonhealthdatascience/intro-open-sim/tree/main). (MIT Licence) - who themselves also cite Law. Simulation Modeling and Analysis 4th Ed. Pages 14 - 17. | `simulation/monitoredresource.py` |
| Tom Monks (2024) [HPDM097 - Making a difference with health data](https://github.com/health-data-science-OR/stochastic_systems) (MIT Licence). | `simulation/warmupauditor.py`<br>`notebooks/analysis.ipynb`<br>`notebooks/choosing_replications.ipynb`<br>`notebooks/choosing_warmup.ipynb` |
| Monks T and Harper A. Improving the usability of open health service delivery simulation models using Python and web apps (https://doi.org/10.3310/nihropenres.13467.2) [version 2; peer review: 3 approved]. NIHR Open Res 2023, 3:48.<br>Who themselves cite a [Stack Overflow](https://stackoverflow.com/questions/59406167/plotly-how-to-filter-a-pandas-dataframe-using-a-dropdown-menu) post. | `notebooks/analysis.ipynb` |

### Funding

This project was developed as part of the project STARS: Sharing Tools and Artefacts for Reproducible Simulations. It is supported by the Medical Research Council [grant number [MR/Z503915/1](https://gtr.ukri.org/projects?ref=MR%2FZ503915%2F1)].