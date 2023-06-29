#!/bin/bash
isort --profile black -l 79 .
black -l 79 .
line_length=E501
unused_var=F841
ambiguous_var=E741
flake8 --extend-ignore E203,$line_length,$unused_var,$ambiguous_var .
