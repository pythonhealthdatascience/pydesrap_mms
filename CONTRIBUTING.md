# Contributing

Thank you for your interest in contributing! 🤗

This file covers:

* 🐞 Workflow for bug reports, feature requests and documentation improvements
* 🚀 Workflow for code contributions (bug fixes, enhancements)
* 🛠️ Development and testing
* 📦 Updating the package
* 🤝 Code of conduct

<br>

## 🐞 Workflow for bug reports, feature requests and documentation improvements

Before opening an issue, please search [existing issues](https://github.com/pythonhealthdatascience/pydesrap_mms/issues) to avoid duplicates. If an issue exists, you can add a comment with additional details and/or upvote (👍) the issue. If there is not an existing issue, please open one and provide as much detail as possible.

* **For feature requests or documentation improvements**, please describe your suggestion clearly.
* **For bugs**, include:
    * Steps to reproduce.
    * Expected and actual behaviour.
    * Environment details (operating system, python version, dependencies).
    * Relevant files (e.g. problematic `.qmd` files).

### Handling bug reports (for maintainers):

* Confirm reproducibility by following the reported steps.
* Label the issue appropriately (e.g. `bug`).
* Request additional information if necessary.
* Link related issues or pull requests.
* Once resolved, close the issue with a brief summary of the fix.

<br>

## 🚀 Workflow for code contributions (bug fixes, enhancements)

1. Fork the repository and clone your fork.

2. Create a new branch for your feature or fix:

```{.bash}
git checkout -b my-feature
```

3. Make your changes and commit them with clear, descriptive messages using the [conventional commits standard](https://www.conventionalcommits.org/en/v1.0.0/).

4. Push your branch to your fork:

```{.bash}
git push origin my-feature
```

5. Open a pull request against the main branch. Describe your changes and reference any related issues.

<br>

## 🛠️ Development and testing

### Dependencies

Set up the Python environment using `conda` (recommended):

```
conda env create --file environment.yaml
conda activate
```

There is also a `requirements.txt` file whcih can be used to set up the environment with `virtualenv`, but this won't fetch a specific version of Python - so please note the version listed in `environment.yaml`.

<br>

### Docstrings

We follow the [numpydoc](https://numpydoc.readthedocs.io/en/latest/format.html) style for docstrings.

<br>

### Tests

Run all tests (with coverage):

```{.bash}
pytest --cov
```

Run tests in parallel:

```{.bash}
pytest -n auto
```

Run an individual test file:

```{.bash}
pytest tests/testfile.py
```

Run a specific test:

```{.bash}
pytest tests/testfile.py::testname
```

<br>

### Linting

Lint all files:

```{.bash}
bash lint.sh
```

Lint a specific `.py` file:

```{.bash}
pylint simulation/model.py
```

Lint a specific `.ipynb` file:

```{.bash}
nbqa pylint notebooks/analysis.ipynb
```

<br>

## 📦 Updating the package

If you are a maintainer and need to publish a new release:

1. Update the `CHANGELOG.md`.

2. Update the version number in `simulation/__init__.py` and `CITATION.cff`, and update the date in `CITATION.cff`.

3. Create a release on GitHub, which will automatically archive to Zenodo.

<br>

## 🤝 Code of conduct

Please be respectful and considerate. See the [code of conduct](https://github.com/pythonhealthdatascience/pydesrap_mms/blob/main/CODE_OF_CONDUCT.md) for details.