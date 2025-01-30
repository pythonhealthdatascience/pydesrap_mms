#!/bin/bash

echo "Linting model code..."
pylint ./simulation

echo "Linting tests..."
pylint ./tests

echo "Linting notebooks..."
nbqa pylint ./notebooks

echo "Linting time-weighted averages notebook..."
nbqa pylint ./docs/time_weighted_averages.ipynb