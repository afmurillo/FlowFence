#!/bin/bash
pylint -d=C0322,C0323,C0324,C0326,W1001,E1002,E1001,C0301,W0311,W0312 --output-format=html $1.py > pylintOutput/$1.html
