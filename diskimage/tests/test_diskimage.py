import pytest
import pytsk3
import diskimage


#
# Provide some data to test
#
# We read in some data to be used for testing later on
# This also test DiskImage.from_file()
@pytest.fixture
def image():
    i = diskimage.DiskImage.from_file('data/mini.dd')
    assert isinstance(i, diskimage.DiskImage)
    return i


@pytest.fixture
def items(image):
    return list(image.find(r'mini-inner.dd'))


#
# Provide some classes for testing purposes
#
class InfoType(object):
    def __init__(self, ftype=0):
        super()
        self.ftype = ftype


class FSType(object):
    def __init__(self, ftype=0):
        super()
        self.info = InfoType(ftype=ftype)


#
# Testing begins here
#
##############################################
# Testing the methods of the DiskImage class #
##############################################

# Test instantiation of the DiskImage class
def test_init_diskimage():
    image = diskimage.DiskImage()
    assert isinstance(image, diskimage.DiskImage)


# Test getting items from a disk image
def test_diskimage_get_items(image):
    # Non-recursive listing
    items = list(image.get_items(recursive=False))
    assert len(items) == 49
    # Recursive listing, should be default
    items = list(image.get_items())
    assert len(items) == 81
    items = list(image.get_items(recursive=True))
    assert len(items) == 81


# Test searching for files within a diskimage
def test_diskimage_find(image):
    assert list(image.find("Non-existing-name", recursive=True, ignorecase=True)) == []
    assert len(list(image.find(r".*\.tXt$", recursive=True, ignorecase=True, regex=True))) == 8
    assert len(list(image.find(r".*\.tXt$", recursive=True, ignorecase=False, regex=True))) == 0
    assert len(list(image.find(r".*\.tXt$", recursive=False, regex=True))) == 6
    assert len(list(image.find(r"mini-inner.dd"))) == 1
    assert len(list(image.find(r".*mini-inner.dd$", regex=True))) == 1


# Test metadata of the DiskImage class
# This indirectly also tests DiskImage.get_filesystems()
def test_diskimage_meta(image):
    assert image.name == 'mini.dd'
    assert image.parents == []
    assert len(image.filesystems) == 2
    assert isinstance(image.filesystems[0], diskimage.filesystem.FileSystem)
    assert isinstance(image.filesystems[1], diskimage.filesystem.FileSystem)


# Test instantiation of a DiskImage from items from within a DiskImage
def test_diskimage_from_items(items):
    image = diskimage.DiskImage.from_items(items, imagename='mini-inner.dd')
    assert isinstance(image, diskimage.DiskImage)
    image = diskimage.DiskImage.from_items(items, imagename='mini-inner')
    assert isinstance(image, diskimage.DiskImage)


####################
# Additional tests #
####################

# Test reading split .e01 images
def test_split_e01():
    # Only run test if pyewf is available
    try:
        import pyewf
        i = diskimage.DiskImage.from_file('data/split.E01')
        assert isinstance(i, diskimage.DiskImage)
    except ImportError:
        pass

# Test if NTFS filesystem test works
def test_isNTFS():
    x = FSType(ftype=pytsk3.TSK_FS_TYPE_NTFS)
    assert diskimage.IsNTFS(x) is True
    x = FSType(ftype=0)
    assert diskimage.IsNTFS(x) is False


# Test getting imagetype from the file-extension
def test_get_imagetype():
    assert diskimage.get_imagetype('image.dd') == diskimage.IMAGE_DD
    assert diskimage.get_imagetype('image.e01') == diskimage.IMAGE_EWF
    assert diskimage.get_imagetype('image.unknown') == diskimage.IMAGE_UNKNOWN


# Test getting a imagehandle from items
def test_get_imagehandle(items):
    i = diskimage.get_imagehandle(items, diskimage.IMAGE_DD)
    assert i
    i = diskimage.get_imagehandle(items, diskimage.IMAGE_UNKNOWN)
    assert i


# Test getting a imagehandle from items
def test_get_imagehandle_from_file():
    i = diskimage.get_imagehandle_from_file('data/mini.dd', diskimage.IMAGE_DD)
    assert i
    i = diskimage.get_imagehandle_from_file('data/mini.dd', diskimage.IMAGE_UNKNOWN)
    assert i
