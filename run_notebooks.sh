#!/usr/bin/env bash

# Loop through all notebooks in the specified directory
for nb in notebooks/*.ipynb; do
    echo "🏃 Running notebook: $nb"
    
    # Execute and update the notebook in-place
    # With some processing to remove metadata created by nbconvert
    if python -m jupyter nbconvert --to notebook --inplace --execute \
        -TagRemovePreprocessor.remove_input_tags="execution" \
        --ClearMetadataPreprocessor.enabled=True "$nb"; then
        echo "✅ Successfully processed: $nb"
    else
        echo "❌ Error processing: $nb"
    fi
    
    echo "-------------------------"
done
