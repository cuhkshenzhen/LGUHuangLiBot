#! /usr/bin/env bash

rm -f deploy.zip
zip -9 -r deploy.zip . --exclude 'venv/*' '.*/*' '.*' '__pycache__/*'
cd venv/lib/python*/site-packages || exit 1
zip -9 -r ../../../../deploy.zip * --exclude 'setuptools-*/*' 'setuptools/*' 'pip-*/*' 'pip/*' 'pkg_resources-*/*' 'pkg_resources/*' 'wheel-*/*' 'wheel/*' '__pycache__/*' '*-info/*' 'easy_install.py'
cd ../../../../
