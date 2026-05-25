#!/bin/bash

cd /home/homeserver/projects/finance-econ-pipeline || exit 1
source /home/homeserver/projects/finance-econ-pipeline/venv/bin/activate

/home/homeserver/projects/finance-econ-pipeline/venv/bin/python scripts/run_pipeline.py
