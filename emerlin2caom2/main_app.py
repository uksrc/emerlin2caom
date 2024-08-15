# ***********************************************************************
# ******************  CANADIAN ASTRONOMY DATA CENTRE  *******************
# *************  CENTRE CANADIEN DE DONNÉES ASTRONOMIQUES  **************
#
#  (c) 2023.                            (c) 2023.
#  Government of Canada                 Gouvernement du Canada
#  National Research Council            Conseil national de recherches
#  Ottawa, Canada, K1A 0R6              Ottawa, Canada, K1A 0R6
#  All rights reserved                  Tous droits réservés
#
#  NRC disclaims any warranties,        Le CNRC dénie toute garantie
#  expressed, implied, or               énoncée, implicite ou légale,
#  statutory, of any kind with          de quelque nature que ce
#  respect to the software,             soit, concernant le logiciel,
#  including without limitation         y compris sans restriction
#  any warranty of merchantability      toute garantie de valeur
#  or fitness for a particular          marchande ou de pertinence
#  purpose. NRC shall not be            pour un usage particulier.
#  liable in any event for any          Le CNRC ne pourra en aucun cas
#  damages, whether direct or           être tenu responsable de tout
#  indirect, special or general,        dommage, direct ou indirect,
#  consequential or incidental,         particulier ou général,
#  arising from the use of the          accessoire ou fortuit, résultant
#  software.  Neither the name          de l'utilisation du logiciel. Ni
#  of the National Research             le nom du Conseil National de
#  Council of Canada nor the            Recherches du Canada ni les noms
#  names of its contributors may        de ses  participants ne peuvent
#  be used to endorse or promote        être utilisés pour approuver ou
#  products derived from this           promouvoir les produits dérivés
#  software without specific prior      de ce logiciel sans autorisation
#  written permission.                  préalable et particulière
#                                       par écrit.
#
#  This file is part of the             Ce fichier fait partie du projet
#  OpenCADC project.                    OpenCADC.
#
#  OpenCADC is free software:           OpenCADC est un logiciel libre ;
#  you can redistribute it and/or       vous pouvez le redistribuer ou le
#  modify it under the terms of         modifier suivant les termes de
#  the GNU Affero General Public        la “GNU Affero General Public
#  License as published by the          License” telle que publiée
#  Free Software Foundation,            par la Free Software Foundation
#  either version 3 of the              : soit la version 3 de cette
#  License, or (at your option)         licence, soit (à votre gré)
#  any later version.                   toute version ultérieure.
#
#  OpenCADC is distributed in the       OpenCADC est distribué
#  hope that it will be useful,         dans l’espoir qu’il vous
#  but WITHOUT ANY WARRANTY;            sera utile, mais SANS AUCUNE
#  without even the implied             GARANTIE : sans même la garantie
#  warranty of MERCHANTABILITY          implicite de COMMERCIALISABILITÉ
#  or FITNESS FOR A PARTICULAR          ni d’ADÉQUATION À UN OBJECTIF
#  PURPOSE.  See the GNU Affero         PARTICULIER. Consultez la Licence
#  General Public License for           Générale Publique GNU Affero
#  more details.                        pour plus de détails.
#
#  You should have received             Vous devriez avoir reçu une
#  a copy of the GNU Affero             copie de la Licence Générale
#  General Public License along         Publique GNU Affero avec
#  with OpenCADC.  If not, see          OpenCADC ; si ce n’est
#  <http://www.gnu.org/licenses/>.      pas le cas, consultez :
#                                       <http://www.gnu.org/licenses/>.
#
#  $Revision: 4 $
#
# ***********************************************************************
#

"""
This module implements the ObsBlueprint mapping, as well as the workflow 
entry point that executes the workflow.
"""

import pickle
import os
import subprocess

from caom2 import SimpleObservation, ObservationIntentType, Target, Telescope, TypedOrderedDict, Plane, Artifact, \
    ReleaseType, ObservationWriter, ProductType, ChecksumURI, Provenance, Position, Point, Energy, TargetPosition
from setuptools.package_index import socket_timeout

import casa_reader as casa
import measurement_set_metadata as msmd
import inputs_parser as ip
import fits_reader as fr

__all__ = [
    'basename',
    'create_observation',
    'upload_xml',
    'emerlin_main_app'
]


def basename(name):
    """
    Adaptation of os.basename for use with directories, instead of files
    :param name: Full path to directory
    :returns: Name of the directory, without path
    """
    base_name = name.split('/')[-1]
    return base_name


def create_observation(storage_name, xml_out_dir):
    """
    Populates an XML document with caom format metadata, extracted from an input measurement set.
    :param storage_name: Name of measurement set
    :param xml_out_dir: Location for writing the output XML
    :returns: Name of the output xml, id for the observation in the xml file
    """
    obs_id = basename(storage_name)
    ms_dir = storage_name + '/{}_avg.ms'.format(obs_id) # maybe flimsy? depends on the rigidity of the em pipeline
    pickle_file = storage_name + '/weblog/info/eMCP_info.pkl'
    with open(pickle_file, 'rb') as f:
        pickle_obj = pickle.load(f)

    observation = SimpleObservation('collection', obs_id)
    observation.obs_type = 'science'
    observation.intent = ObservationIntentType.SCIENCE

    observation.target = Target('TBD')
    target_name = pickle_obj['msinfo']['sources']['targets']
    print(target_name)
    observation.target.name = target_name
    # observation.target.position = TargetPosition(str(casa.find_mssources(ms_dir)), 'J2000')
    observation.telescope = Telescope(casa.get_obs_name(ms_dir)[0])
    observation.telescope = Telescope('EMERLIN')
    observation.planes = TypedOrderedDict(Plane)

    plane = Plane(obs_id)
    observation.planes[obs_id] = plane

    provenance = Provenance(pickle_obj['pipeline_path'])
    plane.provenance = provenance
    provenance.version = pickle_obj['pipeline_version']
    provenance.project = pickle_obj['msinfo']['project'][0]
    provenance.runID = pickle_obj['msinfo']['run']

    ### These components need their output value to be changed a bit
    # provenance.inputs = pickle_obj['inputs']['fits_path']
    # provenance.keywords = str([key for key, value in pickle_obj['input_steps'].items() if value == 1])

    plane.artifacts = TypedOrderedDict(Artifact)

    artifact = Artifact('uri:{}'.format(storage_name), ProductType.SCIENCE, ReleaseType.META)
    plane.artifacts['uri:{}'.format(storage_name)] = artifact

    meta_data = msmd.get_local_file_info(ms_dir)

    artifact.content_type = meta_data.file_type
    artifact.content_length = meta_data.size
    artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))

    for directory in os.listdir(storage_name + '/weblog/plots/'):
        for plots in os.listdir(storage_name + '/weblog/plots/' + directory + '/'):
            plot_full_name = storage_name + '/weblog/plots/' + directory + '/' + plots
            artifact = Artifact('uri:{}'.format(plot_full_name), ProductType.AUXILIARY, ReleaseType.META)
            plane.artifacts['uri:{}'.format(plot_full_name)] = artifact
            meta_data = msmd.get_local_file_info(plot_full_name)

            artifact.content_type = meta_data.file_type
            artifact.content_length = meta_data.size
            artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))

    for directory in os.listdir(storage_name + '/weblog/images/'):
        for images in os.listdir(storage_name + '/weblog/images/' + directory + '/'):
            if images.endswith('-image.fits'):
                plane_id = storage_name + '/weblog/images/' + directory + '/'
                plane = Plane(plane_id)
                observation.planes[plane_id] = plane
                fits_header_data = fr.header_extraction(plane_id + images)

                position = Position()
                plane.position = position

                plane.position.shape = Point(fits_header_data['ra_deg'], fits_header_data['dec_deg'])
                # plane.position.shape.cval1 = fits_header_data['ra_deg']
                # plane.position.shape.cval2 = fits_header_data['dec_deg']

                energy = Energy()
                plane.energy = energy
                plane.energy.restwav = fits_header_data['central_freq'] # change freq to wav and check against model

                provenance = Provenance(plane_id)
                plane.provenance = provenance
                provenance.version = fits_header_data['wsc_version']
                break

        plane.artifacts = TypedOrderedDict(Artifact)
        for images in os.listdir(storage_name + '/weblog/images/' + directory + '/'):
            images_full_name = storage_name + '/weblog/images/' + directory + '/' + images

            artifact = Artifact('uri:{}'.format(images_full_name), ProductType.AUXILIARY, ReleaseType.META)
            plane.artifacts['uri:{}'.format(images_full_name)] = artifact
            meta_data = msmd.get_local_file_info(images_full_name)

            artifact.content_type = meta_data.file_type
            artifact.content_length = meta_data.size
            artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))





    xml_output_name = xml_out_dir + obs_id + '.xml'

    writer = ObservationWriter()
    writer.write(observation, xml_output_name)

    return xml_output_name, obs_id


def upload_xml(xml_output_name, observation_id, rootca_cert, repo_url_base='https://src-data-repo.co.uk/torkeep/',
               collection='EMERLIN'):
    """
    Upload the xml file to the repository, not functional with current setup
    """
    if rootca_cert is None:
        put_command = ['curl', '-X', 'PUT', '-T', xml_output_name,
                       repo_url_base+collection+'/'+observation_id]
        post_command = ['curl', '-X', 'POST', '-T', xml_output_name,
                        repo_url_base+collection+'/'+observation_id]
    else:
        put_command = ['curl', '-ca', '"'+rootca_cert+'"', '-X', 'PUT', '-T', xml_output_name,
                       repo_url_base+collection+'/'+observation_id]
        post_command = ['curl', '-ca', '"'+rootca_cert+'"', '-X', 'POST', '-T', xml_output_name,
                        repo_url_base+collection+'/'+observation_id]
    # print(put_command)
    # print(post_command)
    # subprocess.call(put_command)
    try:
        subprocess.call(put_command)  # method 405, not allowed
    except subprocess.CalledProcessError:
        subprocess.call(post_command)


def emerlin_main_app(storage_name, rootca=None, xml_dir='.'):
    """
    Create XML and upload to repo
    :param storage_name: Name of measurement set
    :param rootca: loaction of rootca.pem
    :param xml_dir: directory for storage of xml output
    """
    xml_output_file, obs_id = create_observation(storage_name, xml_dir)
    # upload_xml(xml_output_file, obs_id, rootca)
    # add something like this for logging later
    # try:
    #     result = to_caom2()
    #     sys.exit(result)
    # except Exception as e:
    #     logging.error(
    #         f'Failed {APPLICATION} execution for {args} with {str(e)}.')
    #     tb = traceback.format_exc()
    #     logging.error(tb)
    #     sys.exit(-1)
