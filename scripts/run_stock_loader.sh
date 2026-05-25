#!/bin/bash

cd /home/homeserver/projects/finance-econ-pipeline || exit 1

echo "======================================"
echo "Stock loader started at: $(date)"
echo "Working directory: $(pwd)"
echo "Python path: /home/homeserver/projects/finance-econ-pipeline/venv/bin/python"

source /home/homeserver/projects/finance-econ-pipeline/venv/bin/activate

/home/homeserver/projects/finance-econ-pipeline/venv/bin/python scripts/load_stock_prices.py

echo "Stock loader finished at: $(date)"
echo "======================================"
