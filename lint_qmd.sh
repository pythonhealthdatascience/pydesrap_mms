#!/bin/bash

# Directory to search for .qmd files
DIRECTORY=${1:-.}

# Linter to use (default to flake8)
LINTER=${2:-flake8}

# Validate the linter choice
if [[ "$LINTER" != "flake8" && "$LINTER" != "pylint" ]]; then
    echo -e "\033[1mError: Unsupported linter. Please choose either 'flake8' or 'pylint'.\033[0m"
    echo
    exit 1
fi

# Temporary file to store extracted Python code
TEMP_FILE=$(mktemp)

# Loop through all .qmd files in the directory
find "$DIRECTORY" -name "*.qmd" | while read -r FILE; do
    echo
    echo "--------------------------------------------------------------------"
    echo "Linting Python code in: $FILE"
    echo "WARNING: Line numbers may be wrong, so section with error is shown"
    echo "--------------------------------------------------------------------"
    echo

    # Extract Python code blocks and save to TEMP_FILE
    awk '
        /```{python}/ {code=1; next}
        /```/ {code=0; next}
        code {print $0}
    ' "$FILE" > "$TEMP_FILE"

    # Check if the temp file is not empty
    if [ -s "$TEMP_FILE" ]; then
        # Run the linter on the extracted code and capture the output
        echo "Linting extracted code..."
        echo
        
        # Store seen errors to avoid duplicates
        declare -A seen_errors

        $LINTER "$TEMP_FILE" 2>&1 | while read -r LINE; do
            # Ignore the file path part in the linter's output
            # The format is typically something like: /tmp/tmp.bKSqCNR0PZ:28:1:
            if [[ "$LINE" =~ [^:]+:([0-9]+):([0-9]+)-?([0-9]+)*: ]]; then
                # Extract the line and column number, and the error message
                LINTER_LINE=${BASH_REMATCH[1]}  # Get the line number
                MESSAGE=${LINE#*:}  # Get the error message after the file and line info
                MESSAGE=$(echo "$MESSAGE" | sed 's/^[0-9]*: //') # Strip off any leading line number if present

                # Check if this error has already been processed
                if [[ -z "${seen_errors[$LINTER_LINE]}" ]]; then
                    # Mark this error as seen
                    seen_errors[$LINTER_LINE]=1

                    # Print the linter message in bold
                    echo -e "\033[1m$MESSAGE\033[0m"
                    echo

                    # Find the corresponding line in the original .qmd file
                    ORIGINAL_LINE=$(sed -n "${LINTER_LINE}p" "$TEMP_FILE")

                    # Print the context: 2 lines above, current line, and 2 lines below
                    sed -n "$((LINTER_LINE - 2)),$((LINTER_LINE + 2))p" "$TEMP_FILE" | while read -r CONTEXT_LINE; do
                        echo "  $CONTEXT_LINE"
                    done

                    echo
                    echo
                fi
            else
                # Print any other output from the linter without modification
                echo "$LINE"
            fi
        done
    else
        echo "No Python code found in $FILE"
    fi
done

# Remove the temporary file
rm -f "$TEMP_FILE"
