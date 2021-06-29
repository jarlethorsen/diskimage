#!/usr/bin/env python3
# diskimage.py by Jarle Thorsen
# -*- coding: utf-8 -*-

import os
import re
import pytsk3
import logging

from diskimage.filesystem import FileSystem

logger = logging.getLogger(__name__)

# We only support .e01 images if pyewf is installed
ewf = True
try:
    import pyewf
except ImportError:
    ewf = False
    logger.debug('pyewf library not found, .e01 images not supported')

# Supported filetype extensions
# '.vhd' and '.vmdk' are not supported yet.
EXTENSIONS = ('.dd', '.000', '.001', '.00001', '.img')
EWFEXTENSIONS = ('.e01', '.s01', '.ex01', '.lx01', '.l01')

if ewf:
    # Add ewf formats to the list of supported extensions
    EXTENSIONS += EWFEXTENSIONS

# Define constants for image types
IMAGE_UNKNOWN = 0
IMAGE_DD = 1
IMAGE_EWF = 2


class DiskImage:
    """A class for handling a Disk Image

    Attributes:
        filesystems (list): a list of diskimage.FileSystem objects found within the image
        name: Name of the image file
        parents (list): a list of objects indicating where this DiskImage is
            located in a recursive listing
    """

    def __init__(self, name=None, parents=[]):
        self.name = name

        self.parents = parents
        self.filesystems = []

    def get_items(self, recursive=True):
        """A generator that yields diskimage.Item objects

        All filesystems found in DiskImage will be traversed

        Args:
            recursive (bool, optional): If recursive is True, then any
                DiskImages found will also be traversed

        Yields:
            an Item-object
        """
        if self.filesystems:
            parents = self.parents
            parents.append(self.name)
            for i, filesystem in enumerate(self.filesystems):
                fsparents = parents.copy()
                fsparents.append('fs' + str(i))
                for item in filesystem.get_items(recursive=True):
                    item.parents = fsparents
                    yield item
                    if recursive:
                        if item.name.lower().endswith(EXTENSIONS):
                            logger.info(f'Trying to open {item.name}...')
                            diparents = fsparents.copy()
                            di = DiskImage.from_items([item], imagename=item.name, parents=diparents)
                            if di.filesystems:
                                logger.info(f'Found {len(di.filesystems)} filesystems!')
                                yield from di.get_items()
        else:
            logger.debug(f'No filesystems found in diskimage {self.name}')

    def find(self, string, recursive=True, ignorecase=True, regex=False):
        """A generator that will yield diskimage.Item objects where name or path matches

        Args:
            string (str): The string to search for. Can be treated as regex
                by setting regex argument to True.
            recursive (bool, optional): if True, it will also search in subdirs
            ignorecase (bool, optional): if True, then the matching will be
                case insensitive
            regex (bool, optional): if True, search using regex. The regex will
                be matched against the complete path,like '/Windows/tmp/file.jpg'

        Yields:
            Item object
        """
        if regex:
            # Set up regex pattern
            if ignorecase:
                pattern = re.compile(string, flags=re.IGNORECASE)
            else:
                pattern = re.compile(string)

        for item in self.get_items(recursive=recursive):
            if regex:
                fullpath = os.path.join(item.path, item.name)
                if pattern.match(fullpath):
                    yield item
            else:
                if ignorecase:
                    if item.name.upper() == string.upper():
                        yield item
                else:
                    if item.name == string:
                        yield item

    @staticmethod
    def get_filesystems(imagehandle):
        """Get a list of diskimage.FileSystem objects from imagehandle

        Args:
            imagehandle: A handle to a disk image

        Returns:
            list: A list of FileSystem objects found in disk image
        """
        # Try to get partitiontable
        filesystems = []
        try:
            partitionTable = pytsk3.Volume_Info(imagehandle)
        except OSError as e:
            if 'Error opening Volume_Info: Cannot determine partition type' in str(e):
                partitionTable = None
        except (IOError, RuntimeError) as e:
            logger.exception(str(e))
            # close open handles
            imagehandle.close()
            return None

        filesystemObject = None

        if partitionTable is not None:
            # Iterate all partitions.
            # We need to manually check the filesystem (filesystemObject.info.ftype) for each partition,
            # partition.desc is not reliable for recent versions of Windows
            for partition in partitionTable:
                logger.debug(f'Partition {partition.addr} at sector {partition.start}')
                try:
                    filesystemObject = FileSystem(imagehandle, offset=(partition.start * 512))
                except (OSError, IOError) as e:
                    logger.debug('Partition %d:\n%s' % (partition.addr, str(e)))
                    # We just go to next partition
                    continue

                # Add found filesystems to list
                fs = 'NTFS' if IsNTFS(filesystemObject) else '*unknown*'
                filesystemObject.fstype = fs
                filesystems.append(filesystemObject)
        else:
            # Found no partition table so we try to open the image as a volume
            try:
                filesystemObject = FileSystem(imagehandle)
            except OSError as e:
                if "Cannot determine file system type" not in str(e):
                    logger.exception(str(e))
            except IOError as e:
                logger.exception(str(e))

            if filesystemObject:
                # Add found filesystems to list
                fs = 'NTFS' if IsNTFS(filesystemObject) else '*unknown*'
                filesystemObject.fstype = fs
                filesystems.append(filesystemObject)

        logger.debug(f'Returning {len(filesystems)} FileSystems')
        return filesystems

    @staticmethod
    def from_file(imagefile):
        """Return a DiskImage object form a local file

        Args:
            imagefile (str): filepath of the imagefile to open

        Returns:
            DiskImage instance initialized with data from imagefile
        """
        di = DiskImage(name=os.path.basename(imagefile))
        if not os.path.isfile(imagefile):
            logger.debug(f'Unable to open file {imagefile}')
            return None
        imagetype = get_imagetype(imagefile)
        imagehandle = get_imagehandle_from_file(imagefile, imagetype)

        if imagehandle:
            di.filesystems = di.get_filesystems(imagehandle)
            return di
        else:
            return None

    @staticmethod
    def from_items(items, imagename="", parents=[]):
        """Takes a list of one or more diskimage.Item objects and returns a DiskImage object

        Args:
            items (list): list of Items
            imagename (string, optional): Name describing the image
            parents (list, optional): A list describing the relative location of
                where items are located.

        Returns:
            DiskImage/None: Returns DiskImage on success, else None
        """
        imagehandle = None
        di = DiskImage(name=imagename, parents=parents)
        imagetype = get_imagetype(di.name)
        imagehandle = get_imagehandle(items, imagetype)

        if imagehandle:
            di.filesystems = di.get_filesystems(imagehandle)
            return di
        else:
            return None


class TSKFileSystemImage(pytsk3.Img_Info):
    """Pytsk3 image object using a file-like object.
    """

    def __init__(self, file_object):
        """Initializes an image object.

        Args:
            file_object (FileIO): file-like object.

        Raises:
            ValueError: if the file-like object is invalid.
        """
        if not file_object:
            raise ValueError('Missing file-like object.')
        # pytsk3.Img_Info does not let you set attributes after initialization.
        self._file_object = file_object
        # Using the old parent class invocation style otherwise some versions
        # of pylint complain also setting type to RAW or EXTERNAL to make sure
        # Img_Info does not do detection.
        tsk_img_type = getattr(
            pytsk3, 'TSK_IMG_TYPE_EXTERNAL', pytsk3.TSK_IMG_TYPE_RAW)
        # Note that we want url to be a binary string in Python 2 and a Unicode
        # string in Python 3. Hence the string is not prefixed.
        pytsk3.Img_Info.__init__(self, url='', type=tsk_img_type)

    def close(self):
        """Closes the volume IO object.
        """
        self._file_object = None

    def read(self, offset, size):
        """Reads a byte string from the image object at the specified offset.

        Args:
            offset (int): offset where to start reading.
            size (int): number of bytes to read.

        Returns:
            bytes: data read.
        """
        self._file_object.seek(offset, os.SEEK_SET)
        return self._file_object.read(size)

    def get_size(self):
        """Retrieves the size.

        Returns:
            int: number of bytes
        """
        return self._file_object.get_size()


class ExtPytskImg_Info(pytsk3.Img_Info):
    """Extends pytsk3 to also support reading disk image within another disk image

    Attributes:
        handle (TYPE): Description
    """

    def __init__(self, handle):
        """Initialize the class

        Args:
            handle: handle to the diskimage
        """
        self.handle = handle
        super(ExtPytskImg_Info, self).__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        """Close the handle"""
        self.handle.close()

    def read(self, offset, size):
        """Read bytes from the disk image

        Args:
            offset (int): Offset to read data from
            size (int): Number of bytes to read

        Returns:
            bytes
        """
        self.handle.seek(offset)
        return self.handle.read(size)

    def get_size(self):
        """Get size of file

        Returns:
            int: Size of file in bytes
        """
        return self.handle.get_media_size()


class ewf_Img_Info(pytsk3.Img_Info):
    """Extends pytsk3 to also support .e01 via pyewf"""

    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        super(ewf_Img_Info, self).__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        """Close the handle to the imagefile"""
        self._ewf_handle.close()

    def read(self, offset, size):
        """Read bytes from the disk image

        Args:
            offset (int): Offset to read data from
            size (int): Number of bytes to read

        Returns:
            bytes
        """
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        """Get size of file

        Returns:
            int: Size of file in bytes
        """
        return self._ewf_handle.get_media_size()


def IsNTFS(filesystemObject):
    """Determines if the file system is NTFS.

    Args:
        filesystemObject (pytsk3 filesystem): The filesystem to check

    Returns:
        bool: A boolean value indicating the file system is NTFS.
    """
    tsk_fs_type = filesystemObject.info.ftype
    return tsk_fs_type in [pytsk3.TSK_FS_TYPE_NTFS, pytsk3.TSK_FS_TYPE_NTFS_DETECT]


def get_imagetype(filename):
    """Return a constant indicating which type of imagefile this is

    Args:
        filename (string): Name of imagefile

    Returns:
        constant: IMAGE_EWF -  filetype supported by pyewf
                  IMAGE_DD  -  filetype supported by pytsk
                  IMAGE_UNKNOWN - unknown filetype
    """
    # Imagetype supported by pyewf
    if filename.lower().endswith(EWFEXTENSIONS):
        if ewf is False:
            logger.warning(f'''File {filename} is of type ewf, but this
                filetype is not supported since module pyewf was not found!''')
        return IMAGE_EWF
    # Imagetype supported by pytsk
    elif filename.lower().endswith(EXTENSIONS):
        return IMAGE_DD
    else:
        return IMAGE_UNKNOWN


def get_imagehandle(items, imagetype):
    """Get imagehandle from list of Items

    Args:
        items (list): list of one or more Item objects to open handle from
        type (int): a constant indicating type of image
            IMAGE_EWF -  filetype supported by pyewf
            IMAGE_DD  -  filetype supported by pytsk
            IMAGE_UNKNOWN - unknown filetype
    """
    imagehandle = None
    if imagetype == IMAGE_EWF:
        ewf_handle = pyewf.handle()
        file_objects = [item.open() for item in items]
        ewf_handle.open_file_objects(file_objects)
        imagehandle = ewf_Img_Info(ewf_handle)
    elif imagetype == IMAGE_DD:
        filehandle = items[0].open()
        if filehandle:
            imagehandle = TSKFileSystemImage(filehandle)
        else:
            logger.debug(f'Unable to open filehandle to {items[0].name}')
    else:
        # Unknown type, time to bruteforce!
        for imagetype in [IMAGE_DD, IMAGE_EWF]:
            imagehandle = get_imagehandle(items, imagetype)
            if imagehandle:
                break
    return imagehandle


def get_imagehandle_from_file(imagefile, imagetype):
    """Get imagehandle from list of Items

    Args:
        items (list): list of one or more Item objects to open handle from
        type (int): a constant indicating type of image
            IMAGE_UNKNOWN - unknown filetype
            IMAGE_DD  -  filetype supported by pytsk
            IMAGE_EWF -  filetype supported by pyewf
    """
    imagehandle = None
    if imagetype == IMAGE_EWF and ewf is True:
        # Use pyewf
        logger.debug(f'Trying to get ewf imagehandle on {imagefile}...')
        if imagefile.lower().endswith(EWFEXTENSIONS):
            filenames = pyewf.glob(imagefile)
        else:
            # Assume the image is not split into multiple parts
            filenames = [imagefile]
        ewf_handle = pyewf.handle()
        try:
            ewf_handle.open(filenames)
        except Exception:
            return None
        imagehandle = ewf_Img_Info(ewf_handle)
    elif imagetype == IMAGE_DD:
        # Use plain pytsk
        logger.debug('Trying to get pytsk imagehandle..')
        imagehandle = pytsk3.Img_Info(imagefile)
    elif imagetype == IMAGE_UNKNOWN:
        # Unknown type, time to bruteforce!
        for imagetype in [IMAGE_EWF, IMAGE_DD]:
            imagehandle = get_imagehandle_from_file(imagefile, imagetype)
            if imagehandle:
                break
    return imagehandle
