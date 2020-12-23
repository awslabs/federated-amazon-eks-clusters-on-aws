#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh
#

# Get reference for all important folders
template_dir="$PWD"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist and node_modules folders"
echo "------------------------------------------------------------------------------"
echo "find $source_dir/cdk-vpc-peering -iname "node_modules" -type d -exec rm -r "{}" \; 2> /dev/null"
find $source_dir/cdk-vpc-peering -iname "node_modules" -type d -exec rm -r "{}" \; 2>/dev/null
echo "find $source_dir/cdk-vpc-peering -iname "dist" -type d -exec rm -r "{}" \; 2> /dev/null"
find $source_dir/cdk-vpc-peering -iname "dist" -type d -exec rm -r "{}" \; 2>/dev/null
echo "find ../ -type f -name 'package-lock.json' -delete"
find $source_dir/cdk-vpc-peering -type f -name 'package-lock.json' -delete

echo "------------------------------------------------------------------------------"
echo "[Test] CDK VPC Peering"
echo "------------------------------------------------------------------------------"
cd $source_dir/cdk-vpc-peering
npm install
npm test

echo "------------------------------------------------------------------------------"
echo "[Test] Compile python files"
echo "------------------------------------------------------------------------------"
cd $source_dir/eksfedctl
python3 -m compileall .
