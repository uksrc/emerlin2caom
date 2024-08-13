## Initial changes to emerlin2caom2. 

The codebase takes a measurement set as an input, extracts the relevant metadata to an xml file, and attempts to upload it to 
The changes are exclusive to python files contained within the emerlin2caom/emerlin2caom directory. As such, there are still some artefacts from the old repository that include: the Dockerfile, the scripts directory, the testing suite. These are left in for now, to be updated when the development environment is finished. 

## Changes in the codebase

The metadata extraction is handled by casa_reader.py and measurement_set_metadata.py. The former handles metadata extracted from the measurement set itself via casa, whereas the latter handles "file" metadata such as size, hashvalue, and locations/names. 

The code for creation of caom observations is contained within main_app.py. It implements the metadata extraction of the other two modules, creates the python object observation, converts it to an XML file, and has command for upload to the repository via curl (not currently functional). 

## Installation and running

Required packages are:

[cadcutils](https://github.com/opencadc/cadctools/tree/main/cadcutils)
[caom2tools](https://github.com/opencadc/caom2tools/tree/main)
[casatools](https://pypi.org/project/casatools/)
[checksumdir](https://pypi.org/project/checksumdir/)

Whilst the docker container is not required for the creation of the XML document, it is needed to upload the data to it. 
For attempting upload, [Stephen's docker-compose setup](https://github.com/uksrc/caomdev) should be built and running. 

Installation is a little odd right now as the cadc requirements claim to need python>3.8, whereas casatools claims to need python<3.6. Sharon Goliath tested the cadc code with python 3.6 for me and it passed all tests. So install cadcutils and caom2tools in python 3.6, via pip, utilising the --ignore-requires-python option. 

There is a simple test included in "test.py", the xml should be produced but the upload is expected to return a 403 permission denied with the current repository setup. 
