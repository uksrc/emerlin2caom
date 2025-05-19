import os
from os.path import exists
from pathlib import Path
import requests
import pyvo as vo

from caom2 import SimpleObservation, ObservationIntentType, Target, Telescope, TypedOrderedDict, Plane, Artifact, \
    ReleaseType, ObservationWriter, Provenance, Position, Point, Energy, TargetPosition, \
    Interval, TypedSet, Polarization, shape, Proposal, Instrument, DerivedObservation, Time, DataProductType, \
    PolarizationState, DataLinkSemantics, EnergyBand

from pkg_resources import Environment
from setuptools.config.expand import canonic_data_files

from emerlin2caom2 import casa_reader as casa
from emerlin2caom2 import file_metadata as msmd
from emerlin2caom2 import fits_reader as fr
from emerlin2caom2 import settings_file as set_f
from emerlin2caom2 import api_requests as api

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

    base_url = set_f.base_url
    obs_id = basename(storage_name)
    ms_dir_main = storage_name + '/{}_avg.ms'.format(obs_id)  # maybe flimsy? depends on the rigidity of the em pipeline
    ms_dir_spectral = storage_name + '/{}_sp.ms'.format(obs_id)
    pickle_file = storage_name + '/weblog/info/eMCP_info.txt'
    pickle_obj = emcp2dict(pickle_file)
    roles, target_ra, target_dec = role_extractor(pickle_obj)
    polarization_states = {'I': PolarizationState.I,
                         'Q': PolarizationState.Q,
                         'U': PolarizationState.U,
                         'V': PolarizationState.V,
                         'RR': PolarizationState.RR,
                         'LL': PolarizationState.LL,
                         'RL': PolarizationState.RL,
                         'LR': PolarizationState.LR,
                         'XX': PolarizationState.XX,
                         'YY': PolarizationState.YY,
                         'XY': PolarizationState.XY,
                         'YX': PolarizationState.YX,
                         'POLI': PolarizationState.POLI,
                         'FPOLI': PolarizationState.FPOLI,
                         'POLA': PolarizationState.POLA,
                         'EPOLI': PolarizationState.EPOLI,
                         'CPOLI': PolarizationState.CPOLI,
                         'NPOLI': PolarizationState.NPOLI}

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
        position = Position(shape.Circle(centre, radius), shape.MultiShape([shape.Circle(centre, radius)]))
        plane.position = position
        # plane.position.bounds = shape.Circle(centre, radius)
        # should be box but is unsupported by the writer, neither is point

        ### REMOVED AS WE NEED TO ADD "bounds" and "samples" which we do not want
        ### Did they intend to make these quantities mandatory. 
        ### Yes, intended, but can we not get these?
        rest_energy = casa.freq2wl(fits_header_data['central_freq'])
        plane.energy = Energy(Interval(rest_energy, rest_energy), [shape.SubInterval(rest_energy, rest_energy)])
        plane.energy.rest = rest_energy

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
        plane.energy = Energy(Interval(msmd_dict["wl_lower"], msmd_dict["wl_upper"]), [shape.SubInterval(msmd_dict["wl_lower"], msmd_dict["wl_upper"])]) 

        plane.energy.bandpass_name = str(msmd_dict["bp_name"])
        
        plane.energy.sample_size = msmd_dict["chan_res"]
        plane.energy.dimension = msmd_dict["nchan"]      
 
        # Plane Time Object (2.5 bounds, samples required)
        # If more than one time sample needed, then use a for loop to add samples.
        time_sample = shape.SubInterval(ms_other["obs_start_time"], ms_other["obs_stop_time"])
        time_bounds = Interval(ms_other["obs_start_time"], ms_other["obs_stop_time"])
        plane.time = Time(time_bounds, [time_sample])
        
        #plane.time.exposure = msmd_dict["int_time"]
        #plane.time.dimension = msmd_dict["num_scans"]

        # Polarisation (Polarization) object needs at least one state as arg.
        # For now this is hard-coded, as this is the only way I can get it to pass xml validation.
        # The states values cannot be comprised of any strings or funcions. 

        pol_dim = int(ms_other["polar_dim"])
        pol_states = (ms_other["polar_states"])
        plane.polarization = Polarization(dimension=pol_dim, states=[self.polarization_states[pol] for pol in pol_states])

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
        # observation.proposal = Proposal(casa_info['prop_id']) # Un-comment once vo-dml sorted for proposal.id
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

        self.ingest_manager(observation.uri, xml_output_name)

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

        # observation.proposal = Proposal(casa_info['prop_id']) # Uncomment once vo-dml sorted for proposal.id

        xml_output_name = self.xml_out_dir + self.obs_id + '_' + target_name + '.xml'
        writer = ObservationWriter()
        writer.write(observation, xml_output_name)

        self.ingest_manager(observation.uri, xml_output_name)

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
            observation.members.add(simple_observation.uri)

        target_information = casa.target_position_all(self.ms_dir_main)
        for i, targ in enumerate(target_information["name"]):
            simple_observation = self.build_simple_observation_target(casa_info, targ, target_information["ra"][i],
                                                                      target_information["dec"][i])
            observation.members.add(simple_observation.uri)

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
        plane.data_product_type = DataProductType('visibility')
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

        # If uploading is enabled, check for existing data records matching uri.
        # If a single record exists, and replacing data is enabled, then delete and
        # replace.  If multiple records exist then log error for analysis. 
        self.ingest_manager(observation.uri, xml_output_name)

    def ingest_manager(self, obs_uri, xml_output_name):
        """
        Conditional to check for existing records, upload status, and unexpected duplicates,
        and decide what to do next, with warnings/prints to log.  
        :obs_uri: uri from observation i.e. TS8004_C_001_20190801_1252+5634
        :param xml_output_name: xml file containing metadata to ingest.  
        """ 
        if set_f.upload:
            machine_id = api.find_existing(self, obs_uri)
            if machine_id:
                if set_f.replace_old_data and isinstance(machine_id, str):
                    del_stat = api.request_delete(self, machine_id)
                    if del_stat == 204:
                        print(obs_uri + " deleted.")
                    else:
                        print(obs_uri + " attempted delete with status code: " + str(del_stat))
                    create_stat = api.request_post(self, xml_output_name)
                    if create_stat == 201:
                        print(obs_uri + " ingested.")
                    else:
                        print(obs_uri + "attempted update with status code: " + create_stat)
                else:
                    print("Multiple records found; no action taken.")
            else:
                create_stat = api.request_post(self, xml_output_name)
                if create_stat == 201:
                    print(obs_uri + " ingested.")
                else:
                    print(obs_uri + " attempted insert with status code: " + str(create_stat))


