#!/usr/bin/env bash

# Get the conda environment's jupyter path
CONDA_JUPYTER=$(dirname "$(which python)")/jupyter

run_notebook() {
    local nb="$1"
    echo "🏃 Running notebook: $nb"
    if "${CONDA_JUPYTER}" nbconvert --to notebook --inplace --execute \
        --ClearMetadataPreprocessor.enabled=True \
        --ClearMetadataPreprocessor.clear_notebook_metadata=False \
        --ClearMetadataPreprocessor.preserve_cell_metadata_mask="kernelspec" \
        "$nb"
    then
        echo "✅ Successfully processed: $nb"
    else
        echo "❌ Error processing: $nb"
    fi
    echo "-------------------------"
}

if [[ -n "$1" ]]; then
    run_notebook "$1"
else
    for nb in notebooks/*.ipynb; do
        run_notebook "$nb"
    done
fi