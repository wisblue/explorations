import nbformat
import ipynbname
from pathlib import Path
import os


def save_nb(g):
    fipynb = g['__vsc_ipynb_file__']
    nb_fname = Path(fipynb).stem
    nb_path = os.path.dirname(fipynb)

    # Load the notebook
    notebook = nbformat.read(fipynb, as_version=4)

    fn = os.path.join(nb_path, nb_fname + ".py")
    with open(fn, 'w') as f:
        # Loop through each cell 
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                lines = cell.source.split('\n')
                #print(lines)
                if lines[0].strip() == '#@save':
                    f.write('\n'.join(lines[1:]))
                    f.write('\n')
    print('script save at ', fn)