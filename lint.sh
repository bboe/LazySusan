#!/bin/bash

dir=$(dirname $0)

# pep8
output=$(find $dir -name [A-Za-z_]\*.py -exec pep8 {} \;)
if [ -n "$output" ]; then
    echo "---pep8---"
    echo -e "$output"
    exit 1
fi

# pylint
output=$(pylint lazysusan 2> /dev/null)
if [ -n "$output" ]; then
    echo "--pylint--"
    echo -e "$output"
fi

# pyflakes
output=$(find $dir -name [A-Za-z_]\*.py -exec pyflakes {} \;)
if [ -n "$output" ]; then
    echo "--pyflakes--"
    echo -e "$output"
    exit 1
fi

exit 0