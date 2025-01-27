import os
from hashlib import md5

from cadcutils.util import date2ivoa
from checksumdir import dirhash


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


def basename(name):
    """
    Adaptation of os.basename for use with directories, instead of files
    :param name: Full path to directory
    :returns: Name of the directory, without path
    """
    # if name[-1] == '/':
    #    name += '/'
    # The if statement above may need to be included for directories with the filename at the end
    base_name = os.path.dirname(name).split('/')[-1]
    return base_name


def get_size(start_path='.'):
    """
    Get the size of all objects contained within an input directory, recursively.
    :param start_path: Name of directory to find size for
    :returns: Total size of the contents of start_path in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


def get_file_type(fqn):
    """
    Basic header extension to content_type lookup.
    :param fqn: Name and path of input data
    :returns: Content type
    """
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
    elif lower_fqn.endswith('.pkl'):
        return 'python/pickle'
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
        file_id = os.path.dirname(fqn).split('/')[-1]

    else:
        file_id = os.path.basename(fqn)
        s = os.stat(fqn)
        file_size = s.st_size
        hash_md5 = md5()
        with open(fqn, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        final_hash_val = hash_md5.hexdigest()

    meta = FileInfo(
        id=file_id,
        size=file_size,
        md5sum=final_hash_val,
        file_type=file_type_local,
    )
    return meta
