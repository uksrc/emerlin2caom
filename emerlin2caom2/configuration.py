from caom2pipe.manage_composable import Config, StorageName

COLLECTION = 'EMERLIN'
SCHEME = 'cadc'
PREVIEW_SCHEME = 'cadc'

def test_config():
    config = Config()
    config.collection = COLLECTION
    config.preview_scheme = PREVIEW_SCHEME
    config.scheme = SCHEME
    config.logging_level = 'INFO'
    StorageName.collection = config.collection
    StorageName.preview_scheme = config.preview_scheme
    StorageName.scheme = config.scheme
    StorageName.data_source_extensions = config.data_source_extensions
    return config
