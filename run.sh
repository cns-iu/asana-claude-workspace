#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 asana_report.py "$@"
