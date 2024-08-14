# emerlin2caom

code to import [e-MERLIN](https://www.e-merlin.ac.uk) [pipeline](https://github.com/e-merlin/eMERLIN_CASA_pipeline) products into the [CAOM](https://github.com/opencadc/caom2)

## Installation and running

Required packages are:

[cadcutils](https://github.com/opencadc/cadctools/tree/main/cadcutils)
[caom2tools](https://github.com/opencadc/caom2tools/tree/main)
[casatools](https://pypi.org/project/casatools/)
[checksumdir](https://pypi.org/project/checksumdir/)

Creating a conda environment to test the commands
```
conda create -n emerlin2caom python=3.6
conda activate emerlin2caom
pip install casatools
pip install checksumdir
pip install caom2 --ignore-requires-python
```
Download the github repositories [cadcutils](https://github.com/opencadc/cadctools/tree/main/cadcutils) and [caom2tools](https://github.com/opencadc/caom2tools/tree/main), change directories to each of their respective download locations and install via the following command.
```
pip install . --ignore-requires-python
```

Whilst the docker container is not required for the creation of the XML document, it is needed to upload the data to the repository (itself). 
For attempting upload, [Stephen's docker-compose setup](https://github.com/uksrc/caomdev) should be built and running. 

There is a simple test included in "test.py", the xml should be produced but the upload is expected to return a 403 permission denied with the current repository setup. 
Change the input values within the file as necessary

