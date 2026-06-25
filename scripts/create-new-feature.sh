#!/bin/bash
echo "Script start"
set -x
# Create a new feature with branch, directory structure, and template
# Usage: ./create-new-feature.sh "feature description"
#        ./create-new-feature.sh --json "feature description"

echo "Setting up..."
set -e

JSON_MODE=false

# Collect non-flag args
echo "Parsing arguments"
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--json] <feature_description>";exit 0 
            ;;
        *)
            ARGS+=("$arg") 
            ;;
    esac
done

FEATURE_DESCRIPTION="${ARGS[*]}"
echo "Feature description: $FEATURE_DESCRIPTION"
if [ -z "$FEATURE_DESCRIPTION" ]; then
        echo "Usage: $0 [--json] <feature_description>" >&2
        exit 1
fi

# Get repository root
echo "Getting repo root"
REPO_ROOT=$(git rev-parse --show-toplevel)
echo "Repo root: $REPO_ROOT"
SPECS_DIR="$REPO_ROOT/specs"
echo "Specs dir: $SPECS_DIR"

# Create specs directory if it doesn't exist
echo "Creating specs directory"
mkdir -p "$SPECS_DIR"

# Find the highest numbered feature directory
echo "Finding highest feature number"
HIGHEST=0
if [ -d "$SPECS_DIR" ]; then
    for dir in "$SPECS_DIR"/*;
    do
        if [ -d "$dir" ]; then
            dirname=$(basename "$dir")
            number=$(echo "$dirname" | grep -o '^[0-9]\+' || echo "0")
            number=$((10#$number))
            if [ "$number" -gt "$HIGHEST" ]; then
                HIGHEST=$number
            fi
        fi
    done
fi
echo "Highest feature number: $HIGHEST"

# Generate next feature number with zero padding
NEXT=$((HIGHEST + 1))
FEATURE_NUM=$(printf "%03d" "$NEXT")
echo "Next feature number: $FEATURE_NUM"

# Create branch name from description
echo "Creating branch name"
BRANCH_NAME=$(echo "$FEATURE_DESCRIPTION" | \
    tr '[:upper:]' '[:lower:]' | \
    sed 's/[^a-z0-9]/-/g' | \
    sed 's/-\+/-/g' | \
    sed 's/^-//' | \
    sed 's/-$//')
echo "Branch name from description: $BRANCH_NAME"

# Extract 2-3 meaningful words
WORDS=$(echo "$BRANCH_NAME" | tr '-' '\n' | grep -v '^$' | head -3 | tr '\n' '-' | sed 's/-$//')
echo "Words for branch name: $WORDS"

# Final branch name
BRANCH_NAME="${FEATURE_NUM}-${WORDS}"
echo "Final branch name: $BRANCH_NAME"

# Create and switch to new branch
echo "Creating and switching to new branch"
git checkout -b "$BRANCH_NAME"

# Create feature directory
echo "Creating feature directory"
FEATURE_DIR="$SPECS_DIR/$BRANCH_NAME"
mkdir -p "$FEATURE_DIR"

# Copy template if it exists
echo "Copying template"
TEMPLATE="$REPO_ROOT/templates/spec-template.md"
SPEC_FILE="$FEATURE_DIR/spec.md"

if [ -f "$TEMPLATE" ]; then
    cp "$TEMPLATE" "$SPEC_FILE"
else
    echo "Warning: Template not found at $TEMPLATE" >&2
    touch "$SPEC_FILE"
fi

echo "Outputting JSON"
if $JSON_MODE; then
    printf '{"BRANCH_NAME":"%s","SPEC_FILE":"%s","FEATURE_NUM":"%s"}\n' \
        "$BRANCH_NAME" "$SPEC_FILE" "$FEATURE_NUM"
else
    # Output results for the LLM to use (legacy key: value format)
    echo "BRANCH_NAME: $BRANCH_NAME"
    echo "SPEC_FILE: $SPEC_FILE"
    echo "FEATURE_NUM: $FEATURE_NUM"
fi
echo "Script end"
