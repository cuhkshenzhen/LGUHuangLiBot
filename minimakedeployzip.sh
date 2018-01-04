#! /usr/bin/env bash

rm -f deploy.zip
zip -r deploy.zip . --exclude 'venv/*' '.*/*' '.*' '__pycache__/*' '*.txt'
cd venv/lib/python*/site-packages || exit 1
zip -r ../../../../deploy.zip * --exclude 'setuptools-*/*' 'setuptools/*' 'pip-*/*' 'pip/*' 'pkg_resources-*/*' 'pkg_resources/*' 'wheel-*/*' 'wheel/*' '__pycache__/*' '*-info/*' 'easy_install.py' 'boto3-*/*' 'boto3/*' 'botocore-*/*' 'botocore/*' 'docutils-*/*' 'docutils/*' 's3transfer/*' 's3transfer-*/*' 'dateutil-*/*' 'dateutil/*' 'docutils/*' 'docutils-*/*' 'jmespath-*/*' 'jmespath/*'
cd ../../../../
