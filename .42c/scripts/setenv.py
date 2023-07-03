import json
import os

def set_env(name, value):
    with open(os.environ['GITHUB_ENV'], 'a') as fh:
        print(f'{name}={value}', file=fh)

def set_output(name, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f'{name}={value}', file=fh)

set_env ("token1", "env-value1")
set_output ("token1", "output-value")