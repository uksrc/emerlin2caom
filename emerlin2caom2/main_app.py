import os
from os.path import exists
from pathlib import Path
import requests

from caom2 import SimpleObservation, ObservationIntentType, Target, Telescope, TypedOrderedDict, Plane, Artifact, \
    ReleaseType, ObservationWriter, Provenance, Position, Point, Energy, TargetPosition, \
    Interval, TypedSet, Polarization, shape, Proposal, Instrument, DerivedObservation, Time, DataProductType, \
    PolarizationState, DataLinkSemantics, EnergyBand

from pkg_resources import Environment
from setuptools.config.expand import canonic_data_files

import casa_reader as casa
import file_metadata as msmd
import fits_reader as fr
import settings_file as set_f

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

def role_extractor(pickle_dict):
    targets = pickle_dict['targets'].split(',')
    phase_cal = pickle_dict['phscals'].split(',')
    flux_cal = pickle_dict['fluxcal'].split(',')
    band_pass_cal = pickle_dict['bpcal'].split(',')
    point_cal = pickle_dict['ptcal'].split(',')
    
    role_rev = {}
    for i, x in enumerate(targets):
        role_rev[x] = "target_{}".format(i)
        role_rev[phase_cal[i]] = "phase_calibrator_{}".format(i)

    for i, x in enumerate(flux_cal):
        role_rev[x] = "flux_calibrator"

    for i, x in enumerate(band_pass_cal):
            role_rev[x] = "band_pass_calibrator"

    for i, x in enumerate(point_cal):
        role_rev[x] = "pointing_calibrator"

    target_names = role_rev.keys()
    print(target_names)
    name_ra = []
    name_dec = []
    for name in target_names:
        split_name = name.split('+')
        if len(split_name) == 1:
            split_name = name.split('-')
        name_ra.append(split_name[0])
        name_dec.append(split_name[1])

    return role_rev, name_ra, name_dec

def basename(name):
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

class EmerlinMetadata:
    """
    Populates an XML document with caom format metadata, extracted from an input measurement set.
    :param storage_name: Name of measurement set
    :param xml_out_dir: Location for writing the output XML
    :returns: Name of the output xml, id for the observation in the xml file
    """
    storage_name = set_f.storage_name
    xml_out_dir = set_f.xmldir
    if xml_out_dir[-1] != '/':
        xml_out_dir += '/'

    base_url = 'https://src-data-repo.co.uk/torkeep/observations/EMERLIN'
    rootca = set_f.rootca
    ska_token = set_f.ska_token
    obs_id = basename(storage_name)
    ms_dir_main = storage_name + '/{}_avg.ms'.format(obs_id)  # maybe flimsy? depends on the rigidity of the em pipeline
    ms_dir_spectral = storage_name + '/{}_sp.ms'.format(obs_id)
    pickle_file = storage_name + '/weblog/info/eMCP_info.txt'
    pickle_obj = emcp2dict(pickle_file)
    roles, target_ra, target_dec = role_extractor(pickle_obj)


    def artifact_metadata(self, observation, plane_id, artifact_full_name, plots):
        """
        Creates metadata for physical artifacts, including type, size and hash value
        :param observation: observation class to add artifact to
        :param plane_id: plane to add artifact metadata to
        :param artifact_full_name: full location of target object
        :param plots: name of artifact only, no path
        """
        plane = observation.planes[plane_id]
        art_uri = 'uri:{}'.format(plots)

        artifact = Artifact(art_uri, DataLinkSemantics.AUXILIARY, ReleaseType.DATA)
        plane.artifacts[art_uri] = artifact
        meta_data = msmd.get_local_file_info(artifact_full_name)

        artifact.content_type = meta_data.file_type
        artifact.content_length = meta_data.size
        artifact.content_checksum = 'md5:{}'.format(meta_data.md5sum)


    def fits_plane_metadata(self, observation, fits_full_name, images, plane_id):
        """
        Creates metadata for fits files, currently includes only basic information with scope to add more
        :param observation: Class to add metadata to
        :param fits_full_name: String format name and path to fits file
        :param images: String name of fits file, no path
        :param plane_id: String id to allocate correct plane
        :returns: plane created for fits file to be passed to the artifact function
        """

        plane = observation.planes[plane_id]
        fits_header_data = fr.header_extraction(fits_full_name + images)

        position = Position()
        plane.position = position
        ra_pos = fits_header_data['ra_deg']
        print(ra_pos)
        if ra_pos < 0:
            ra_pos += 360 # Does this make sense for converting negative to positive ra? should it just be the absolute?
        dec_pos = fits_header_data['dec_deg']
        centre = Point(ra_pos, dec_pos)
        width = abs(fits_header_data['pix_width'] * fits_header_data['pix_width_scale'])
        height = abs(fits_header_data['pix_length'] * fits_header_data['pix_length_scale'])
        radius = 0.5 * width
        # plane.position.bounds = shape.Box(centre, radius)
        plane.position.bounds = shape.Circle(centre, radius)
        # should be box but is unsupported by the writer, neither is point

        energy = Energy()
        plane.energy = energy
        plane.energy.restwav = casa.freq2wl(fits_header_data['central_freq'])  # change freq to wav and check against model

        provenance = Provenance(images)
        plane.provenance = provenance
        provenance.version = fits_header_data['wsc_version']


    def measurement_set_metadata(self, observation, ms_dir, plane_id):
        """
        Creates metadata for measurement sets, extracting infomation from the ms itself, as well as the pickle file
        :param observation:  Class to add metadata to
        :param ms_dir: string path and name of measurement set
        :returns: Plane class where data was added
        """

        ms_name = basename(ms_dir)
        msmd_dict = casa.msmd_collect(ms_dir, self.pickle_obj['targets'])

        ms_other = casa.ms_other_collect(ms_dir)     

        # plane = Plane(ms_name)
        plane = observation.planes[plane_id]

        #Release date to-do convert to ivoa:datetime
        plane.data_release = ms_other["data_release"]

        # Make an Energy object for this Plane (bounds,samples required)
        esample = shape.SubInterval(msmd_dict["wl_lower"], msmd_dict["wl_upper"])
        ebounds = Interval(msmd_dict["wl_lower"], msmd_dict["wl_upper"])
        plane.energy = Energy(ebounds, [esample])

        plane.energy.bandpass_name = str(msmd_dict["bp_name"])
        
        plane.energy.sample_size = msmd_dict["chan_res"]
        plane.energy.dimension = msmd_dict["nchan"]      
 
        # This doesn't break anything but also isn't printed to xml. caom2.5?
        plane.energy.energy_bands = TypedSet('Radio')

        # Plane Time Object (2.5 bounds, samples required)
        time_sample = shape.SubInterval(ms_other["obs_start_time"], ms_other["obs_stop_time"])
        time_bounds = Interval(ms_other["obs_start_time"], ms_other["obs_stop_time"])
        plane.time = Time(time_bounds, [time_sample])
        
        #plane.time.exposure = msmd_dict["int_time"]
        #plane.time.dimension = msmd_dict["num_scans"]

        # Polarisation (Polarization) object needs at least one state as arg.

        pol_dim = int(ms_other["polar_dim"])
        pol_states = ms_other["polar_states"] 
        plane.polarization = Polarization(dimension = pol_dim, states = pol_states)

        # adjustment for different pipeline versions
        pipeline_name = self.pickle_obj['pipeline_path'].split('/')[-1]
        if len(pipeline_name) == 0:
            pipeline_name = self.pickle_obj['pipeline_path'].split('/')[-2]

        provenance = Provenance(pipeline_name)
        plane.provenance = provenance
        provenance.version = self.pickle_obj['pipeline_version']
        provenance.project = msmd_dict['prop_id']
        provenance.run_id = self.pickle_obj['run']

        plane.artifacts = TypedOrderedDict(Artifact)

        art_uri = 'uri:{}'.format(ms_name)

        artifact = Artifact(art_uri, DataLinkSemantics.THIS, ReleaseType.DATA)
        plane.artifacts[art_uri] = artifact

        meta_data = msmd.get_local_file_info(ms_dir)

        artifact.content_type = meta_data.file_type
        artifact.content_length = meta_data.size
        artifact.content_checksum = 'md5:{}'.format(meta_data.md5sum)

        return plane
        ### These components need their output value to be changed somewhat
        # provenance.inputs = pickle_obj['fits_path']
        # provenance.keywords = str([key for key, value in pickle_obj['input_steps'].items() if value == 1])


    def build_simple_observation_telescope(self, casa_info, ante_id):
        """
        :param casa_info: dictionary of metadata extracted from measurement set
        :param ante_id: antenna id, int
        :returns: the caom observation created
        """
        observation = SimpleObservation('EMERLIN', '{}_{}'.format(self.obs_id, casa_info['antennas'][int(ante_id)]))
        observation.obs_type = 'science'
        observation.intent = ObservationIntentType.SCIENCE

        observation.telescope = Telescope(casa_info['tel_name'][0])
        observation.proposal = Proposal(casa_info['prop_id'])
        cart_coords = casa.polar2cart(casa_info['ante_pos'][ante_id]['m0']['value'],
                                     casa_info['ante_pos'][ante_id]['m1']['value'],
                                     casa_info['ante_pos'][ante_id]['m2']['value'])

        instrument_name = casa_info['antennas'][ante_id]


        observation.telescope.geo_location_x = cart_coords['x']
        observation.telescope.geo_location_y = cart_coords['y']
        observation.telescope.geo_location_z = cart_coords['z']
        observation.instrument = Instrument(instrument_name)


        xml_output_name = self.xml_out_dir + self.obs_id + '_' + casa_info['antennas'][int(ante_id)] + '.xml'
        writer = ObservationWriter()
        writer.write(observation, xml_output_name)

        if set_f.upload:
            if set_f.replace_old_data:
                self.request_delete(xml_output_name)
            self.request_put(xml_output_name)

        return observation


    def build_simple_observation_target(self, casa_info, target_name, target_ra, target_dec):
        """
        :param casa_info: dictionary of metadata extracted from measurement set
        :param target_name: name of target object, string
        :param target_ra: ra of target in degrees, float
        :param target_dec: dec of target in degrees, float
        :returns: the CAOM observation created the target object
        """
        observation = SimpleObservation('EMERLIN', '{}_{}'.format(self.obs_id, target_name))
        observation.obs_type = 'science'
        observation.intent = ObservationIntentType.SCIENCE

        point = Point(target_ra, target_dec)

        observation.target = Target('TBD')
        observation.target.name = target_name
        observation.target_position = TargetPosition(point, 'Equatorial') # J2000?
        observation.target_position.equinox = 2000.

        observation.proposal = Proposal(casa_info['prop_id'])

        xml_output_name = self.xml_out_dir + self.obs_id + '_' + target_name + '.xml'
        writer = ObservationWriter()
        writer.write(observation, xml_output_name)

        if set_f.upload:
            if set_f.replace_old_data:
                self.request_delete(xml_output_name)
            self.request_put(xml_output_name)

        return observation


    def build_metadata(self):
        """
        Builds metadata for e-merlin pipeline output, including main and calibration measurement sets, fits images,
        plots and pickle file metadata. The target measurement set and output destination are defined within the
        settings_file.py.
        """

        casa_info = casa.msmd_collect(self.ms_dir_main, self.pickle_obj['targets'])
        # casa_other = casa.ms_other_collect(self.ms_dir_main)
        observation = DerivedObservation('EMERLIN', self.obs_id, 'correlator')

        for tele in range(len(casa_info['antennas'])):
            simple_observation = self.build_simple_observation_telescope(casa_info, tele)
            observation.members.add(str(simple_observation.uri))

        target_information = casa.target_position_all(self.ms_dir_main)
        for i, targ in enumerate(target_information["name"]):
            simple_observation = self.build_simple_observation_target(casa_info, targ, target_information["ra"][i],
                                                                      target_information["dec"][i])
            observation.members.add(str(simple_observation.uri))

        observation.obs_type = 'science'
        observation.intent = ObservationIntentType.SCIENCE

        observation.telescope = Telescope(casa_info['tel_name'][0])

        observation.planes = TypedOrderedDict(Plane)

        plane_id_list = []
        for plane_target in casa_info['mssources']:
            plane = Plane(plane_target)
            observation.planes[plane_target] = plane
            pipeline_name = self.pickle_obj['pipeline_path'].split('/')[-1]
            if len(pipeline_name) == 0:
                pipeline_name = self.pickle_obj['pipeline_path'].split('/')[-2]
            provenance = Provenance(pipeline_name)
            # adjustment for difference in naming between measurement set and info file
            # if '+' in plane_target:
            #     split_name = plane_target.split('+')
            #     # maybe add a loop here to see if the components fit into the targ ra/dec
            #     plane_target_adjusted = split_name[0][0:4] + '+' + split_name[1][0:4]
            # elif '-' in plane_target:
            #     split_name = plane_target.split('-')
            #     plane_target_adjusted = split_name[0][0:4] + '-' + split_name[1][0:4]
            # else:
            plane_target_adjusted = plane_target
            provenance.keywords.add("Role {}".format(self.roles[plane_target_adjusted]))
            plane.provenance = provenance
            provenance.version = self.pickle_obj['pipeline_version']
            provenance.run_id = self.pickle_obj['run']

            plane_id_list.append(plane_target)

        ms_plane_id = basename(self.ms_dir_main)
        plane = Plane(ms_plane_id)
        plane.data_product_type = DataProductType('measurements')
        observation.planes[ms_plane_id] = plane
        plane_id_list.append(ms_plane_id)
        self.measurement_set_metadata(observation, self.ms_dir_main, ms_plane_id)

        my_file = Path(self.ms_dir_spectral)
        if my_file.is_dir():
            sp_plane_id = basename(self.ms_dir_spectral)
            plane = Plane(sp_plane_id)
            observation.planes[sp_plane_id] = plane
            plane_id_list.append(sp_plane_id)
            plane.data_product_type = DataProductType('spectrum')
            self.measurement_set_metadata(observation, self.ms_dir_spectral, sp_plane_id)

        for directory in os.listdir(self.storage_name + '/weblog/plots/'):
            for plots in os.listdir(self.storage_name + '/weblog/plots/' + directory + '/'):
                plot_full_name = self.storage_name + '/weblog/plots/' + directory + '/' + plots
                plane_id_single = [x for x in plane_id_list if x in plots]
                if plane_id_single:
                    self.artifact_metadata(observation, plane_id_single[0], plot_full_name, plots)

        for directory in os.listdir(self.storage_name + '/weblog/images/'):
            main_fits = [x for x in os.listdir(self.storage_name + '/weblog/images/' + directory + '/') if x.endswith('-image.fits')]
            plane_id_full = self.storage_name + '/weblog/images/' + directory + '/'
            if main_fits:
                plane_id_single = [x for x in plane_id_list if x in directory]
                self.fits_plane_metadata(observation, plane_id_full, main_fits[0], plane_id_single[0])
                 # will this break?
                for images in os.listdir(self.storage_name + '/weblog/images/' + directory + '/'):
                    images_full_name = self.storage_name + '/weblog/images/' + directory + '/' + images
                    self.artifact_metadata(observation, plane_id_single[0], images_full_name, images)

        if os.path.isdir(self.storage_name + '/splits/'):
            for directory in os.listdir(self.storage_name + '/splits/'):
                extension = directory.split('.')[-1]
                if extension == 'ms':
                    plane_id_full = self.storage_name + '/splits/' + directory + '/'
                    plane_id_single = [x for x in plane_id_list if x in directory]
                    self.measurement_set_metadata(observation, plane_id_full, plane_id_single[0])
        # currently not handling flag_versions as casa will not read "ms1" version measurement sets
        
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
        #         self.measurement_set_metadata(observation, plane_id_full, pickle_obj)

        # structure of observation outside of functions?
        xml_output_name = self.xml_out_dir + self.obs_id + '.xml'

        writer = ObservationWriter()
        writer.write(observation, xml_output_name)

        if set_f.upload:
            if set_f.replace_old_data:
                self.request_delete(xml_output_name)
            self.request_put(xml_output_name)
            # self.request_put(xml_output_name)
            # if set_f.replace_old_data:
            #     try:
            #         self.request_post(xml_output_name)
            #     except requests.exceptions.RequestException:
            #           pass
            # else:
            #     self.request_put(xml_output_name)

    def url_maker(self, xml_output_name):
        """
        Construction of a URL to be used within a request to the torkeep service.
        :param xml_output_name: ObservationID of object to be targeted by URL
        :returns: URL of the target object and target torkeep collection
        """
        made_url = self.base_url + '/' + '.'.join(xml_output_name.split('/')[-1].split('.')[:-1]).rstrip()
        return made_url

    def request_put(self, xml_output_name):
        """
        Put target XML data onto the database.
        :param xml_output_name: ObservationID of xml file to put
        """
        xml_output_name = xml_output_name
        url_put = self.url_maker(xml_output_name)
        print(repr(url_put)) # can remove once code no longer needs debugging
        put_file = xml_output_name
        headers_put = {'authorization' : 'bearer {}'.format(self.ska_token), 'Content-type': 'text/xml'}
        res = requests.put(url_put, data=open(put_file, 'rb'), verify=self.rootca, headers=headers_put)
        print(res, res.content) # can remove once code no longer needs debugging

    def request_post(self, xml_output_name):
        """
        Post target XML data to the database.
        :param xml_output_name: ObservationID of target xml data
        """
        xml_output_name = xml_output_name.rstrip()
        url_post = self.url_maker(xml_output_name)
        print(repr(url_post)) # can remove once code no longer needs debugging
        post_file = xml_output_name
        print(post_file) # can remove once code no longer needs debugging
        headers_post = {'authorization': 'bearer {}'.format(self.ska_token), 'Content-type': 'text/xml'}
        res = requests.post(url_post, data=open(post_file, 'rb'), verify=self.rootca, headers=headers_post)
        print(res, res.content) # can remove once code no longer needs debugging
        print("URL:", url_post) # can remove once code no longer needs debugging
        print("Response Code:", res.status_code) # can remove once code no longer needs debugging
        print("Response Text:", res.text) # can remove once code no longer needs debugging

    def request_delete(self, to_del):
        """
        Deletes target XML data on the database.
        :param to_del: ObservationID of target data to delete
        """
        url_del = self.url_maker(to_del)
        print(url_del) # can remove once code no longer needs debugging
        headers_del = {'authorization' : 'bearer {}'.format(self.ska_token)}
        res = requests.delete(url_del, verify=self.rootca, headers=headers_del)
        print(res) # can remove once code no longer needs debugging

    def request_get(self, file_to_get=''):
        """
        Get target data from database.
        :param file_to_get: ObservationID of file to get
        """
        url_get = self.base_url + '/' + file_to_get
        print(url_get) # can remove once code no longer needs debugging
        res = requests.get(url_get, verify=self.rootca)
        print(res) # can remove once code no longer needs debugging





