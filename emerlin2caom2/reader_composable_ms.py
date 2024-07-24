import logging

import casatools
import data_util as du


msmd = casatools.msmetadata()

__all__ = [
    'FileInfo',
    'MetadataReader',
    'FileMetadataReader'
]



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


class FileMetadataReader(MetadataReader):
    """Use case: Measurement set files on local disk."""

    def __init__(self):
        super().__init__()

    def _retrieve_file_info(self, key, source_name):
        self._file_info[key] = du.get_local_file_info(source_name)


    def _retrieve_headers(self, key, source_name):
        self._headers[key] = []

        msmd.open(source_name)
        sum_dict = msmd.summary()
        sum_keys = sum_dict.keys()
        msmd.done()

        meta_headers = [key for key in sum_keys if 'observationID' not in key]

        self._headers[key] = meta_headers
