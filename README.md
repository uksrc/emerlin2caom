# emerlin2caom

code to import [e-MERLIN](https://www.e-merlin.ac.uk) [pipeline](https://github.com/e-merlin/eMERLIN_CASA_pipeline) products into the [CAOM](https://github.com/opencadc/caom2)

this has been created from the blank2caom template

## Initial changes to emerlin2caom2.

The codebase takes a measurement set as an input, extracts the relevant metadata to an xml file, and attempts to upload it to
The changes are exclusive to python files contained within the emerlin2caom/emerlin2caom directory. As such, there are still some 
artefacts from the old repository that include: the Dockerfile, the scripts directory, the testing suite. 
These are left in for now, to be updated when the development environment is finished.

## Changes in the codebase

The metadata extraction is handled by casa_reader.py and measurement_set_metadata.py. 
The former handles metadata extracted from the measurement set itself via casa, whereas the latter handles "file" metadata such as size,
hashvalue, and locations/names.

The code for creation of caom observations is contained within main_app.py.
It implements the metadata extraction of the other two modules, creates the python object observation,
converts it to an XML file, and has command for upload to the repository via curl (not currently functional).

## Installation and running

Required packages are:

[cadcutils](https://github.com/opencadc/cadctools/tree/main/cadcutils)
[caom2tools](https://github.com/opencadc/caom2tools/tree/main)
[casatools](https://pypi.org/project/casatools/)
[checksumdir](https://pypi.org/project/checksumdir/)

Creating a conda environment to test the commands
```
conda create -n emerlin2caom python=3.7.6
conda activate emerlin2caom
pip install astropy
pip install casatools
pip install checksumdir
pip install caom2 --ignore-requires-python
```
Download the github repositories [cadcutils](https://github.com/opencadc/cadctools/tree/main/cadcutils) and 
[caom2tools](https://github.com/opencadc/caom2tools/tree/main), change directories to each of their respective download 
locations and install via the following command.
```
pip install . --ignore-requires-python
```

Whilst the docker container is not required for the creation of the XML document, it is needed to upload the data to 
the repository (itself). 
For attempting upload, [Stephen's docker-compose setup](https://github.com/uksrc/caomdev) should be built and running. 

There is a simple test included in "test.py", the xml should be produced but the upload is expected to return a 403 
permission denied with the current repository setup. 
Change the input values within the file as necessary

