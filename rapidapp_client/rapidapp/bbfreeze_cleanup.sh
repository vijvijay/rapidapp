#!/bin/bash

rm dist/ -Rfv
find * | egrep ".*\.pyc$" | while read file; do rm -v "$file"; done
