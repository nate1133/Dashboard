#!/bin/bash

cd /home/homeserver/projects/finance-econ-pipeline || exit 1

echo "======================================"
echo "Macro loader started at: $(date)"
echo "Working directory: $(pwd)"
echo "Python path: /home/homeserver/projects/finance-econ-pipeline/venv/bin/python"

source /home/homeserver/projects/finance-econ-pipeline/venv/bin/activate

/home/homeserver/projects/finance-econ-pipeline/venv/bin/python scripts/load_economic_indicators.py

echo "Macro loader finished at: $(date)"
echo "======================================"
