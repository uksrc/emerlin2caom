import pickle
import os
import subprocess

from caom2 import SimpleObservation, ObservationIntentType, Target, Telescope, TypedOrderedDict, Plane, Artifact, \
    ReleaseType, ObservationWriter, ProductType, ChecksumURI, Provenance, Position, Point, Energy, TargetPosition
# from setuptools.package_index import socket_timeout

import casa_reader as casa
import measurement_set_metadata as msmd
# import inputs_parser as ip
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

    casa_info = casa.msmd_collect(storage_name)

    observation = SimpleObservation('EMERLIN', obs_id)
    observation.obs_type = 'science'
    observation.intent = ObservationIntentType.SCIENCE

    observation.target = Target('TBD')
    target_name = pickle_obj['msinfo']['sources']['targets']
    print(target_name)
    observation.target.name = target_name
    # this needs correcting so that the data format is correct, unsure what it wants right now
    # observation.target.position = TargetPosition(str(casa.find_mssources(ms_dir)), 'J2000')
    observation.telescope = Telescope(casa_info['tel_name'])
    # observation.telescope = Telescope('EMERLIN')
    observation.planes = TypedOrderedDict(Plane)

    plane = Plane(obs_id)
    observation.planes[obs_id] = plane

    provenance = Provenance(basename(pickle_obj['pipeline_path']))
    plane.provenance = provenance
    provenance.version = pickle_obj['pipeline_version']
    provenance.project = pickle_obj['msinfo']['project'][0]
    provenance.runID = pickle_obj['msinfo']['run']

    ### These components need their output value to be changed somewhat
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
            # artifact = Artifact('uri:{}'.format(plot_full_name), ProductType.AUXILIARY, ReleaseType.META)
            # plane.artifacts['uri:{}'.format(plot_full_name)] = artifact
            artifact = Artifact('uri:{}'.format(plots), ProductType.AUXILIARY, ReleaseType.META)
            plane.artifacts['uri:{}'.format(plots)] = artifact
            meta_data = msmd.get_local_file_info(plot_full_name)

            artifact.content_type = meta_data.file_type
            artifact.content_length = meta_data.size
            artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))

    for directory in os.listdir(storage_name + '/weblog/images/'):
        for images in os.listdir(storage_name + '/weblog/images/' + directory + '/'):
            if images.endswith('-image.fits'):
                plane_id_full = storage_name + '/weblog/images/' + directory + '/'
                plane_id = directory
                plane = Plane(images)
                observation.planes[images] = plane
                fits_header_data = fr.header_extraction(plane_id_full + images)

                position = Position()
                plane.position = position

                plane.position.shape = Point(fits_header_data['ra_deg'], fits_header_data['dec_deg'])

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

            # artifact = Artifact('uri:{}'.format(images_full_name), ProductType.AUXILIARY, ReleaseType.META)
            # plane.artifacts['uri:{}'.format(images_full_name)] = artifact
            artifact = Artifact('uri:{}'.format(images), ProductType.AUXILIARY, ReleaseType.META)
            plane.artifacts['uri:{}'.format(images)] = artifact
            meta_data = msmd.get_local_file_info(images_full_name)

            artifact.content_type = meta_data.file_type
            artifact.content_length = meta_data.size
            artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))





    xml_output_name = xml_out_dir + obs_id + '.xml'

    writer = ObservationWriter()
    writer.write(observation, xml_output_name)

    return xml_output_name, obs_id


def upload_xml(xml_output_name, observation_id, rootca_cert, token,
               repo_url_base='https://src-data-repo.co.uk/torkeep/observations/',
               collection='EMERLIN'):
    """
    Upload the xml file to the repository, not functional with current setup
    """
    # if rootca_cert is None:
    #     put_command = ['curl', '-X', 'PUT', '-T', xml_output_name,
    #                    repo_url_base+collection+'/'+observation_id]
    #     post_command = ['curl', '-X', 'POST', '-T', xml_output_name,
    #                     repo_url_base+collection+'/'+observation_id]
    # else:
    #     put_command = ['curl', '--cacert', '"'+rootca_cert+'"', '-v', '--header', '"Content-Type: text/xml"', '--header',
    #                    '"authorization: bearer $SKA_TOKEN"', '-T', xml_output_name,
    #                    repo_url_base+collection+'/'+observation_id]
    #     post_command = ['curl', '--cacert', '"'+rootca_cert+'"', '-X', 'POST', '-T', xml_output_name,
    #                     repo_url_base+collection+'/'+observation_id]
    # # print(put_command)
    # # print(post_command)
    # # subprocess.call(put_command)
    # try:
    #     subprocess.call(put_command)  # method 405, not allowed
    # except subprocess.CalledProcessError:

    # I always need to define rootCa
    # add a promt to regenerate the SKA_TOKEN?
    # How should the POST command be formulated?


    put_command = ['curl', '--cacert', rootca_cert, '-v', '--header', '"Content-Type: text/xml"', '--header',
                       '"authorization: bearer {}"'.format(token), '-T', xml_output_name,
                       repo_url_base+collection+'/'+observation_id]
    # print(put_command)
    return put_command



def emerlin_main_app(storage_name, rootca, token, xml_dir='.'):
    """
    Create XML and upload to repo
    :param storage_name: Name of measurement set
    :param rootca: loaction of rootca.pem
    :param xml_dir: directory for storage of xml output
    :param token: bearer token for access
    """
    xml_output_file, obs_id = create_observation(storage_name, xml_dir)
    put_com = upload_xml(xml_output_file, obs_id, rootca, token)
    print(' '.join(put_com))
    # subprocess.call(put_com) # put command from python does not work, authentication is different
    # x-vo-authenticated vs www-authenticate: Bearer
    # perhaps the requests module could rectify this?
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
