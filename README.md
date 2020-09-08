# How to run visualization

Prepare:
venv, install requirements.txt

Install mozaik (python3):

```
git clone https://github.com/antolikjan/mozaik.git
cd mozaik
git checkout python3
python setup.py install
```

Run in folder mff_nprg045:
```
bokeh serve --show visualize --args path_to_datastore
```
(path_to_datastore example: /home/katterrina/matfyz/rocnikac/vzorove_mozaik/FeedForwardInhibition_student)

Running bokeh server:
* selecting more disjunct areas in plot is posblie with Shift key