#!/bin/bash

dir=$(dirname $0)

# flake8 (runs pep8 and pyflakes)
flake8 $dir
if [ $? -ne 0 ]; then
    echo "Exiting due to flake8 errors. Fix and re-run to finish tests."
    exit $?
fi

# pylint
pylint --rcfile=$dir/.pylintrc $dir/lazysusan 2> /dev/null
exit $?