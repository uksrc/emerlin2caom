import pickle
import os
import subprocess
from os.path import basename

from caom2 import SimpleObservation, ObservationIntentType, Target, Telescope, TypedOrderedDict, Plane, Artifact, \
    ReleaseType, ObservationWriter, ProductType, ChecksumURI, Provenance, Position, Point, Energy, TargetPosition, \
    Interval, TypedSet, Polarization, shape

import casa_reader as casa
import measurement_set_metadata as msmd
import fits_reader as fr
import settings_file as set

__all__ = [
    'EmerlinMetadata',
    'emcp2dict'
]

def emcp2dict(emcp_file):
    '''
    Convert the plain text version of the pickle file to a python dictionary. Using this rather than the pickle file
    removes the constraints of having the same or great version of python packages such as astropy. It is however, not
    as robust. There may be issues in future with conflicting names as I have flattened one layer of structure.
    :param emcp_file: name of pickle file to be read in. x
    :returns: dictionary version of input file
    '''
    with open(emcp_file) as file:
        lines = [line.rstrip() for line in file]
    pickle_dict = {}
    for line in lines:
        line_no_space = "".join(line.split())
        if ':' in line_no_space:
            nested_list = line_no_space.split(':')
            pickle_dict[nested_list[0]] = nested_list[1]
    return pickle_dict

class EmerlinMetadata:
    """
    Populates an XML document with caom format metadata, extracted from an input measurement set.
    :param storage_name: Name of measurement set
    :param xml_out_dir: Location for writing the output XML
    :returns: Name of the output xml, id for the observation in the xml file
    """
    storage_name = set.storage_name
    # rootca = set.rootca
    xml_out_dir = set.xmldir
    # ska_token = set.ska_token

    def basename(self, name):
        """
        Adaptation of os.basename for use with directories, instead of files
        :param name: Full path to directory
        :returns: Name of the directory, without path
        """
        if name[-1] == '/':
            name = name[:-1]
        if '/' not in name:
            base_name = name
        else:
            base_name = name.split('/')[-1]
        return base_name

    def artifact_metadata(self, plane, artifact_full_name, plots):
        '''
        Creates metadata for physical artifacts, including type, size and hash value
        :param plane: plane to add arrtifact metadata to
        :param artifact_full_name: full location of target object
        :param plots: name of artifact only, no path
        '''
        # plot_full_name = storage_name + '/weblog/plots/' + directory + '/' + plots
        artifact = Artifact('uri:{}'.format(plots), ProductType.AUXILIARY, ReleaseType.META)
        plane.artifacts['uri:{}'.format(plots)] = artifact
        meta_data = msmd.get_local_file_info(artifact_full_name)

        artifact.content_type = meta_data.file_type
        artifact.content_length = meta_data.size
        artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))

    def fits_plane_metadata(self, observation, fits_full_name, images):
        '''
        Creates metadata for fits files, currently includes only basic information with scope to add more
        :param observation: Class to add metadata to
        :param fits_full_name: String format name and path to fits file
        :param images: String name of fits file, no path
        :returns: plane created for fits file to be passed to the artifact function
        '''
        # plane_id_full = storage_name + '/weblog/images/' + directory + '/'
        plane = Plane(images)
        observation.planes[images] = plane
        fits_header_data = fr.header_extraction(fits_full_name + images)

        position = Position()
        plane.position = position
        plane.position.shape = Point(fits_header_data['ra_deg'], fits_header_data['dec_deg'])

        energy = Energy()
        plane.energy = energy
        plane.energy.restwav = fits_header_data['central_freq']  # change freq to wav and check against model

        provenance = Provenance(images)
        plane.provenance = provenance
        provenance.version = fits_header_data['wsc_version']

        return plane


    def measurement_set_metadata(self, observation, obs_id, ms_dir, pickle_dict):
        '''
        Creates metadata for measurement sets, extracting infomation from the ms itself, as well as the pickle file
        :param observation:  Class to add metadata to
        :param ms_dir: string path and name of measurement set
        :param pickle_obj: pickle object read in from file
        :returns: Plane class where data was added
        '''

        print(ms_dir)
        ms_name = self.basename(ms_dir)
        msmd_dict = casa.msmd_collect(ms_dir)

        plane = Plane(ms_name)
        observation.planes[ms_name] = plane

        # Make an Energy object for this Plane
        plane.energy = Energy()

        # Assign Energy object metadata
        sample = shape.SubInterval(msmd_dict["wl_lower"], msmd_dict["wl_upper"])
        plane.energy.bounds = Interval(msmd_dict["wl_lower"], msmd_dict["wl_upper"], samples=[sample])
        plane.energy.bandpass_name = str(msmd_dict["bp_name"])

        # These don't break anything but also aren't printed to xml.
        # Waiting on patch for obs_reader_writer.py
        plane.energy.energy_bands = TypedSet('Radio')

        plane.polarization = Polarization()
        # See if polarization will go in for Plane.
        pol_states, dim = casa.get_polar(ms_dir)
        plane.polarization.dimension = int(dim)

        # This one isn't working quite right yet-- see obs_reader_writer.py
        # plane.polarization.polarization_states = pol_states

        # provenance = Provenance(self.basename(pickle_obj['pipeline_path']))
        provenance = Provenance(pickle_dict['pipeline_path'])
        plane.provenance = provenance
        # provenance.version = pickle_obj['pipeline_version']
        provenance.version = pickle_dict['pipeline_version']
        provenance.project = msmd_dict['project']
        provenance.runID = pickle_dict['run']

        plane.artifacts = TypedOrderedDict(Artifact)

        artifact = Artifact('uri:{}'.format(ms_name), ProductType.SCIENCE, ReleaseType.META)
        plane.artifacts['uri:{}'.format(ms_name)] = artifact

        meta_data = msmd.get_local_file_info(ms_dir)

        artifact.content_type = meta_data.file_type
        artifact.content_length = meta_data.size
        artifact.content_checksum = ChecksumURI('md5:{}'.format(meta_data.md5sum))

        return plane
        ### These components need their output value to be changed somewhat
        # provenance.inputs = pickle_obj['inputs']['fits_path']
        # provenance.keywords = str([key for key, value in pickle_obj['input_steps'].items() if value == 1])

    def build_metadata(self):
        '''
        Builds metadata for emerlin pipeline output, including main and calibration measurment sets, fits images,
        plots and pickle file metadata. The target measurment set and output destination are definied within the
        settings_file.py.
        '''
        obs_id = self.basename(self.storage_name)
        ms_dir = self.storage_name + '/{}_avg.ms'.format(obs_id) # maybe flimsy? depends on the rigidity of the em pipeline
        pickle_file = self.storage_name + '/weblog/info/eMCP_info.txt'
        pickle_obj = emcp2dict(pickle_file)
        casa_info = casa.msmd_collect(ms_dir)

        observation = SimpleObservation('EMERLIN', obs_id)
        observation.obs_type = 'science'
        observation.intent = ObservationIntentType.SCIENCE

        observation.target = Target('TBD')
        # target_name = pickle_obj['msinfo']['sources']['targets']
        target_name = pickle_obj['targets']
        observation.target.name = target_name
        # this needs correcting so that the data format is correct, unsure what it wants right now
        # observation.target.position = TargetPosition(str(casa.find_mssources(ms_dir)), 'J2000')
        observation.telescope = Telescope(casa_info['tel_name'][0])
        observation.planes = TypedOrderedDict(Plane)

        plane = self.measurement_set_metadata(observation, obs_id, ms_dir, pickle_obj)

        for directory in os.listdir(self.storage_name + '/weblog/plots/'):
            for plots in os.listdir(self.storage_name + '/weblog/plots/' + directory + '/'):
                plot_full_name = self.storage_name + '/weblog/plots/' + directory + '/' + plots
                self.artifact_metadata(plane, plot_full_name, plots)

        for directory in os.listdir(self.storage_name + '/weblog/images/'):
            main_fits = [x for x in os.listdir(self.storage_name + '/weblog/images/' + directory + '/') if x.endswith('-image.fits')]
             # will this break?
            if len(main_fits) > 0:
                plane_id_full = self.storage_name + '/weblog/images/' + directory + '/'
                plane = self.fits_plane_metadata(observation, plane_id_full, main_fits[0])
                for images in os.listdir(self.storage_name + '/weblog/images/' + directory + '/'):
                    images_full_name = self.storage_name + '/weblog/images/' + directory + '/' + images
                    self.artifact_metadata(plane, images_full_name, images)


        # removed for now but this structure can be used for auxiliary measurement sets in future
        # for directory in os.listdir(self.storage_name + '/weblog/calib/'):
        #     extension = directory.split('.')[-1]
        #     if extension in ['txt', 'pkl']:
        #         pass
        #     elif extension == 'png':
        #         # do not know how to assign this ancillary data product to the proper plane
        #         unprocessed_plots = [directory]
        #     else:
        #         # may want to add try, except clause here when completed for robustness
        #         plane_id_full = self.storage_name + '/weblog/calib/' + directory + '/'
        #         self.measurement_set_metadata(observation, obs_id, plane_id_full, pickle_obj)

        # structure of observation outside of functions?
        xml_output_name = self.xml_out_dir + obs_id + '.xml'

        writer = ObservationWriter()
        writer.write(observation, xml_output_name)






