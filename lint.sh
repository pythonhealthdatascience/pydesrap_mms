#!/bin/bash

echo "Linting model code..."
pylint ./simulation

echo "Linting tests..."
pylint ./tests

echo "Linting notebooks..."
nbqa pylint ./notebooks