#!/bin/bash

CURRENT_DIR=$(pwd)
TEMP_DIR=$(mktemp -d)

cd $TEMP_DIR

# Install code2prompt if not already installed
if ! command -v code2prompt &> /dev/null; then
    pip install code2prompt
fi

# Download the adk-docs repo
git clone https://github.com/google/adk-docs.git
git clone https://github.com/google/adk-samples.git

# Convert the adk-docs repo to a large markdown file
code2prompt \
    -f "*.py,*.md" \
    -e "*test*" \
    -p "adk-docs/docs/get-started" \
    -p "adk-docs/docs/callbacks" \
    -p "adk-docs/docs/events" \
    -p "adk-docs/docs/artifacts" \
    -p "adk-docs/docs/context" \
    -p "adk-docs/docs/agents" \
    -p "adk-docs/examples/python/agent-samples/youtube-shorts-assistant" \
    -p "adk-docs/docs/tutorials/agent-team.md" \
    -p "adk-docs/examples/python/tutorial/agent_team/adk-tutorial" \
    -o adk_docs.md

# Convert the adk-samples repo to a large markdown file
code2prompt \
    -f "*.py,*.md" \
    -e "*test*" \
    -p "adk-samples/python/agents/software-bug-assistant" \
    -p "adk-samples/python/agents/data-science" \
    -p "adk-samples/python/agents/fomc-research" \
    -o adk_samples.md

# Copy the adk-docs.md file to the current directory
cp $TEMP_DIR/adk_docs.md $CURRENT_DIR/adk_agent/adk_docs.md
cp $TEMP_DIR/adk_samples.md $CURRENT_DIR/adk_agent/adk_samples.md
cd $CURRENT_DIR

# Remove the temporary directory
rm -rf $TEMP_DIR