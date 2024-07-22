import os
from hashlib import md5
from checksumdir import dirhash
import casatools

msmd = casatools.msmetadata()

__all__ = [
    'FileInfo',
    'MetadataReader',
    'FileMetadataReader'
]

class FileInfo:
    """
    Container for the metadata of a file:
        - ID
        - size
        - name
        - md5sum
        - file_type
        - encoding
    """
    def __init__(self, id, size=None, name=None, md5sum=None, lastmod=None,
                 file_type=None, encoding=None):
        if not id:
            raise AttributeError(
                'ID of the file in Storage Inventory is required')
        self.id = id
        self.size = size
        self.name = name
        self.md5sum = md5sum
        self.lastmod = lastmod
        self.file_type = file_type
        self.encoding = encoding

    def __str__(self):
        return (
            'id={}, name={}, size={}, type={}, encoding={}, last modified={}, '
            'md5sum={}'.format(self.id, self.name, self.size, self.file_type,
                               self.encoding, date2ivoa(self.lastmod),
                               self.md5sum))

class MetadataReader:
    """Wrap the mechanism for retrieving metadata from the data source, that is used to create a
    CAOM2 record, and to make decisions about how to create that record. Use
    cases are:
        - FITS files on local disk
        - CADC storage client
        - Gemini http client
        - VOSpace client

    Users of this class hierarchy should be able to reduce the number of
    times file headers and FileInfo are retrieved for the same file.

    Use the source for determining FileInfo information because comparing
    the md5sum at the source to CADC storage is how to determine whether or
    not a file needs to be pushed to CADC for storage, should storing files be
    part of the execution.

    TODO - how to handle thumbnails and previews
    """

    def __init__(self):
        # dicts are indexed by mc.StorageName.destination_uris
        self._headers = {}  # astropy.io.fits.Headers
        self._file_info = {}  # cadcdata.FileInfo
        self._logger = logging.getLogger(self.__class__.__name__)

    def __str__(self):
        file_info_keys = '\n'.join(ii for ii in self._file_info.keys())
        header_keys = '\n'.join(ii for ii in self._headers.keys())
        return f'\nheaders:\n{header_keys}\nfile_info:\n{file_info_keys}'

    @property
    def file_info(self):
        return self._file_info

    @property
    def headers(self):
        return self._headers

    def _retrieve_file_info(self, key, source_name):
        """
        :param key: Artifact URI
        :param source_name: fully-qualified name at the data source
        """
        raise NotImplementedError

    def _retrieve_headers(self, key, source_name):
        """
        :param key: Artifact URI
        :param source_name: fully-qualified name at the data source
        """
        raise NotImplementedError

    def set(self, storage_name):
        """Retrieves the Header and FileInfo information to memory."""
        self._logger.debug(f'Begin set for {storage_name.file_name}')
        self.set_headers(storage_name)
        self.set_file_info(storage_name)
        self._logger.debug('End set')

    def set_file_info(self, storage_name):
        """Retrieves FileInfo information to memory."""
        self._logger.debug(f'Begin set_file_info for {storage_name.file_name}')
        for index, entry in enumerate(storage_name.destination_uris):
            if entry not in self._file_info:
                self._logger.debug(f'Retrieve FileInfo for {entry}')
                self._retrieve_file_info(entry, storage_name.source_names[index])
        self._logger.debug('End set_file_info')

    def set_headers(self, storage_name):
        """Retrieves the Header information to memory."""
        self._logger.debug(f'Begin set_headers for {storage_name.file_name}')
        for index, entry in enumerate(storage_name.destination_uris):
            if entry not in self._headers:
                self._logger.debug(f'Retrieve headers for {entry}')
                self._retrieve_headers(entry, storage_name.source_names[index])
        self._logger.debug('End set_headers')

    def reset(self):
        self._headers = {}
        self._file_info = {}
        self._logger.debug('End reset')

    def unset(self, storage_name):
        """Remove an entry from the collections. Keeps memory usage down over long runs."""
        for entry in storage_name.destination_uris:
            if entry in self._headers:
                del self._headers[entry]
            if entry in self._file_info:
                del self._file_info[entry]
            self._logger.debug(f'Unset the metadata for {entry}')

# the following three functions probably want to be structure in their own module as within the cadc library
# current location is fine for now though


def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

def get_file_type(fqn):
    """Basic header extension to content_type lookup."""
    lower_fqn = fqn.lower()
    if os.path.isdir(fqn):
        return 'application/measurement-set'
    elif lower_fqn.endswith('.fits') or lower_fqn.endswith('.fits.fz') or lower_fqn.endswith('.fits.bz2'):
        return 'application/fits'
    elif lower_fqn.endswith('.gif'):
        return 'image/gif'
    elif lower_fqn.endswith('.png'):
        return 'image/png'
    elif lower_fqn.endswith('.jpg'):
        return 'image/jpeg'
    elif lower_fqn.endswith('.tar.gz'):
        return 'application/x-tar'
    elif lower_fqn.endswith('.csv'):
        return 'text/csv'
    elif lower_fqn.endswith('.hdf5') or fqn.endswith('.h5'):
        return 'application/x-hdf5'
    else:
        return 'text/plain'


def get_local_file_info(fqn):
    """
    Gets descriptive metadata for a directory of measurement set files on disk.
    :param fqn: Fully-qualified name of the file on disk.
    :return: FileInfo, no scheme on the md5sum value.
    """
    file_type_local = get_file_type(fqn)

    if file_type_local == 'application/measurement-set':
        file_size = get_size(fqn)
        final_hash_val = dirhash(fqn)  # very slow, may need to remove in future

    else:
        s = stat(fqn)
        file_size = s.st_size
        hash_md5 = md5()
        with open(fqn, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        final_hash_val = hash_md5.hexdigest()

    meta = FileInfo(
        id=os.path.basename(fqn),
        size=file_size,
        md5sum=final_hash_val,
        file_type=file_type_local,
    )
    return meta


class FileMetadataReader(MetadataReader):
    """Use case: Measurement set files on local disk."""

    def __init__(self):
        super().__init__()

    def _retrieve_file_info(self, key, source_name):
        self._file_info[key] = get_local_file_info(source_name)


    def _retrieve_headers(self, key, source_name):
        self._headers[key] = []

        msmd.open(source_name)
        sum_dict = msmd.summary()
        sum_keys = sum_dict.keys()
        msmd.done()

        meta_headers = [key for key in sum_keys if 'observationID' not in key]

        self._headers[key] = meta_headers
