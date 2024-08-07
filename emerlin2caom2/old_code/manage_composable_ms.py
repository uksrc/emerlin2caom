# place-holder for new manage_composable module
import os

from caom2 import ObservationReader, ObservationWriter

class CadcException(Exception):
    """Generic exception raised by failure cases within the caom2pipe
    module."""

    pass

def read_obs_from_file(fqn):
    """Common code to read a CAOM Observation from a file."""
    if not os.path.exists(fqn):
        raise CadcException(f'Could not find {fqn}')
    reader = ObservationReader(False)
    return reader.read(fqn)


def write_obs_to_file(obs, fqn):
    """Common code to write a CAOM Observation to a file."""
    ow = ObservationWriter()
    ow.write(obs, fqn)