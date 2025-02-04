# emerlin2caom

Code to import [e-MERLIN](https://www.e-merlin.ac.uk) [pipeline](https://github.com/e-merlin/eMERLIN_CASA_pipeline) products into the [CAOM](https://github.com/opencadc/caom2)

This has been created from the blank2caom2 template

## Description

The codebase takes the output directory of the emerlin casa pipeline as an input, extracts the relevant metadata to an
xml file.
The inouts to the code are added via the settings_file.py file. These inputs are:
- storage_name: path to the target emerlin pipeline output (string)
- xmldir: directory where the output xml file will be created
- rootca: path to your rootCA.pem file (string)
- ska_token: access token generated by ska iam

Only storage_name and xmldir are required for xml creation. rootca and ska_token are needed for upload to the database.
However, the python based upload is not yet implemented. 
Once the settings file is filled in, the code can be run using the run_script.py as follows:

```commandline
python run_script.py
```

The expected output is a series of xml files which describes the metadata of the avg.ms, plots (found in weblog/plot),
and fits images (found in weblog/images). The main output is the derived observation which is named according to your 
input e-Merlin data, this contains the majority of the metadata. There are also additional xml files which are simple 
observations and describe the telescopes used within the observation, each is named as with the main output, but will an 
additional tag which indicates the telescope that is modelled. 

Objects that are included within the emerlin output but not the metadata currently are:
- calibration measurement sets (found in weblog/calib),
- input files default_params.json and inputs.ini
- log files from casa and the emerlin pipeline
- the eMERLIN_CASA_pipeline codebase
- observatory.flags
- _avg.ms.flagversions measurement sets
- all html files found within weblog, as well as logs and the emerlin gif

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
pip install astropy=4.5.1
pip install casatools
pip install checksumdir
pip install caom2 --ignore-requires-python
pip install pytest
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

## Alternative installation of  CASA

The casa source is here
https://open-bitbucket.nrao.edu/projects/CASA/repos/casa6/browse

can install wheels from https://casa-pip.nrao.edu/repository/pypi-casa-release/

pip install casatools --extra-index-url https://casa-pip.nrao.edu/repository/pypi-casa-release/


