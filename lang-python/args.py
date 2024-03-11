from argparse import ArgumentParser
import sys
def in_notebook():
    return 'ipykernel' in sys.modules

parser = ArgumentParser() 
parser.add_argument("--verbosity", help="increase output verbosity", default=True)
if in_notebook():
    args = parser.parse_args(args=[])
else:
    args = parser.parse_args()
print(args.verbosity)
print('ipykernel' in sys.modules)
print('IPython' in sys.modules)
