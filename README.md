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

emerlin2caom currently is comprised of a set of functions to interact with the measurement set data product via casatools, casa_reader.py.  This script still needs optimisation, to consolidate the number of opens to as few as possible.

The main_app.py script contains an observation function which assigns metadata to caom elements for observations, planes and artifacts, and writes these to an xml file.  An argument could be made for abstracting this whole function out of main as this is effectively mapping out a 'blueprint'. The syntax needed for various elements by the caom2 code used to produce the XML for the database can be a bit diverse (documentation and data model and some blueprints say 'plane.energy.bandpassName', while what the code requires is actually 'plane.energy.bandpass_name', for example).  However, it may be helpful to see documentation on caom2tools/caom2/caom2 repository.  

For collecting information on the actual data product artifact, the script to determine file type and discern measurement set status is called measurement_set_metadata.py.  This script needs renaming and reworking potentially to respond/interact with main_app.py with regard to determining other data product types such as 'image' or 'plot'.   
