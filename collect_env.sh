#!/bin/bash
set -e

REPORT_DIR=env_report
mkdir -p "$REPORT_DIR"

# Docker information
( docker ps -a ; docker images ) > "$REPORT_DIR/docker_info.txt" 2>&1 || true
( docker-compose ps ) > "$REPORT_DIR/docker_compose_ps.txt" 2>&1 || true

# Python packages
pip freeze > "$REPORT_DIR/pip_freeze.txt" 2>&1 || true

# System packages (optional)
dpkg -l > "$REPORT_DIR/dpkg_l.txt" 2>&1 || true

# Repository listing
git ls-files > "$REPORT_DIR/git_files.txt"

# Archive
tar -czf env_report.tar.gz "$REPORT_DIR"
echo "Environment report saved to env_report.tar.gz"
