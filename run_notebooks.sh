#!/usr/bin/env bash

# Get the conda environment's jupyter path
CONDA_JUPYTER=$(dirname "$(which python)")/jupyter

# Loop through all notebooks in the specified directory
for nb in notebooks/*.ipynb; do
    echo "🏃 Running notebook: $nb"
    
    # Execute and update the notebook in-place
    # With some processing to remove metadata created by nbconvert
    if "${CONDA_JUPYTER}" nbconvert --to notebook --inplace --execute \
        --ClearMetadataPreprocessor.enabled=True \
        --ClearMetadataPreprocessor.clear_notebook_metadata=False \
        --ClearMetadataPreprocessor.preserve_cell_metadata_mask="kernelspec" \
        "$nb"; then
        echo "✅ Successfully processed: $nb"
    else
        echo "❌ Error processing: $nb"
    fi
    
    echo "-------------------------"
done
