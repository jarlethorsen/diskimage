import os
import re
import pytsk3
import logging

import diskimage as di
from diskimage.item import Item

logger = logging.getLogger(__name__)


class FileSystem(pytsk3.FS_Info):
    """Class that contains methods for a FileSystem

    Attributes:
        fstype (string): Type of filesystem
        offset (int): Offset where filesystem is located within image
        parents (list): A list describing the location of the filesystem
    """

    def __init__(self, imagehandle, offset=0, fstype="", parents=[]):
        """Initialize the FileSystem object

        Args:
            imagehandle: handle to the parent diskimage
            offset (int, optional): Offset where filesystem is located within image
            fstype (string, optional): Type of filesystem
            parents (list, optional): A list describing the location of the filesystem
        """
        self.fstype = fstype
        self.offset = offset
        # The parent objects this FileSystem belongs to
        self.parents = []
        super(FileSystem, self).__init__(imagehandle, offset=offset)

    def __bool__(self):
        """Return the bolean status of the class

        Returns:
            bool: False if not able to get the root directoy of FileSystem
        """
        return bool(self.get_directory())

    def get_directory(self, path='/', inode=None):
        """Return a pytsk3.Directory object

        Args:
            path (str, optional): Path to open
            inode (None, optional): Inode of the path

        Returns:
            pytsk3.Directory
        """
        try:
            if inode:
                return self.open_dir(inode=inode)
            else:
                return self.open_dir(path=path)
        except Exception as e:
            logger.exception(f'Unable to open dir: inode={inode}, path={path} {str(e)}')
            return None

    def get_items(self, path='/', inode=None, recursive=False):
        """Get diskimage.Item objects for all entries in directory

        Args:
            path (str, optional): The path to search
            inode (None, optional): The inode to search
            recursive (bool, optional): If recursive == True, it will traverse
                all subdirs recursively

        Yields:
            Item/None: The generator yields None if dir does not exist
        """
        directoryobject = self.get_directory(path=path, inode=inode)
        if directoryobject is None:
            yield None
        for item in directoryobject:
            item = Item.from_pytsk_item(self, path, item)
            if item:
                item.parents = self.parents
                if item.name not in [".", ".."]:
                    # We don't need link to current/parent dir
                    yield item
                    if recursive:
                        # Not all items have a info.meta value, so we have to
                        # catch the exception and just continue
                        try:
                            if item.type == 'dir':
                                subpath = os.path.join(path, item.name)
                                yield from self.get_items(path=subpath, inode=item.inode, recursive=recursive)
                        except Exception:
                            continue

    def find(self, regex, path='/', inode=None, recursive=False, ignorecase=True):
        """Find diskimage.Item objects where name matches regex

        Args:
            regex (string): The regex to search for. The regex will be matched
                against the complete path, like '/Windows/tmp/file.jpg'
            path (str, optional): The path to start searching in
            inode (None, optional): The inode to search
            recursive (bool, optional): if recursive is True, it will also
                search in subdirs
            ignorecase (bool, optional): If True, search will be
                case-insensitive.

        Yields:
            Item: Item object where name matches regex
        """
        if ignorecase:
            pattern = re.compile(regex, flags=re.IGNORECASE)
        else:
            pattern = re.compile(regex)

        for item in self.get_items(path=path, recursive=recursive):
            fullpath = os.path.join(path, item.name)
            if pattern.match(fullpath):
                result = Item.from_pytsk_item(path, item)
                if result:
                    yield result

    def find_diskimages(self, path='/', inode=None, recursive=False):
        """Find disk images

        A disk image is any file with extension matching the list of supported
        disk image types found in diskimage.EXTENSIONS.

        Args:
            path (str, optional): The path to start searching in
            inode (int, optional): The inode of the path to start searching in.
            recursive (bool, optional): if True, it will also search in subdirs

        Yields:
            diskimage.Item: Items where extension matches
        """
        # Create regex to search for
        pattern = r'.*\.('
        for i, extension in enumerate(di.EXTENSIONS):
            pattern += extension[1:]
            if i < len(di.EXTENSIONS) - 1:
                pattern += '|'
            else:
                pattern += ')$'
        logger.debug(f'Searching for {pattern}')
        for path, item in self.find(pattern, path=path, inode=inode, recursive=recursive):
            try:
                f_type = item.info.meta.type
            except Exception:
                continue

            # Skip entry if it is unallocated (deleted)
            if int(item.info.name.flags) & pytsk3.TSK_FS_NAME_FLAG_UNALLOC:
                continue

            # Make sure that it is a regular file and filesize > 0
            if f_type == pytsk3.TSK_FS_META_TYPE_REG and item.info.meta.size != 0:
                yield Item.from_pytsk_item(path, item)

    def find_filesystems(self, path='/', inode=None, recursive=False):
        """Find filesystems

        Args:
            path (str, optional): The path to start searching in
            inode (int, optional): The inode of the path to start searching in
            recursive (bool, optional): If True, also search in subdirs

        Yields:
            tuple: ("path/where/disk-image/found/", [list of filesystems])
        """
        for path, item in self.find_diskimages(path=path, inode=inode, recursive=recursive):
            logger.info(f'Searching for filesystems in {os.path.join(path, item.info.name.name.decode("utf-8"))}')
            diskimage = di.DiskImage.from_bytes([self.get_file_data(inode=item.info.meta.addr)], imagename=item.info.name.name.decode('utf-8'))
            if diskimage:
                if diskimage.filesystems:
                    logger.info(f'Found {len(diskimage.filesystems)} filesystems!')
                    fullpath = os.path.join(path, item.info.name.name.decode('utf-8'))
                    yield (fullpath, diskimage.filesystems)

    def get_dirs(self, path='/', inode=None):
        """Return a list of only dirs found in directory

        Args:
            path (str, optional): Path to search
            inode (None, optional): Inode of path to search

        Returns:
            list: list of directories
        """
        items = [item for _, item in self.dir(path=path, inode=inode)]
        if items:
            return [item for item in items if item.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR]
        else:
            return []

    def get_file_handle(self, file=None, inode=None):
        """Return a file like object of a file by filepath or inode

        Args:
            file (string, optional): File to open
            inode (int, optional): Inode of file to open

        Returns:
            ExtPytskFile: A class describing the open file
        """
        if inode:
            f = self.open_meta(inode=inode)
        elif file:
            f = self.open(file)
        else:
            return None
        return ExtPytskFile(f)

    def extract_files(self, sourcepath, filenames, destination, make_uppercase=False):
        """Extract files from filesystem

        Takes a sourcepath and a list of filenames and copy files to
        destination dir in local filesystem.

        Args:
            sourcepath (string): Path to extract files from
            filenames (list): List of filenames to extract
            destination (string): Path in local filesystem where to extract
                files
            make_uppercase (bool, optional): If True, all filenames will be
                converted to UPPERCASE

        Returns:
            list: List of extracted files
        """
        items = [item for _, item in self.dir(path=sourcepath)]
        if not items or items == [None]:
            return []
        extracted = []
        for item in items:
            try:
                f_type = item.info.meta.type
            except Exception:
                continue

            # Skip entry if it is unallocated (deleted)
            if int(item.info.name.flags) & pytsk3.TSK_FS_NAME_FLAG_UNALLOC:
                continue

            if f_type == pytsk3.TSK_FS_META_TYPE_REG and item.info.meta.size != 0:
                filename = item.info.name.name.decode('utf-8')
                if filename.upper() in [x.upper() for x in filenames]:
                    if make_uppercase:
                        filename = filename.upper()
                    output = os.path.join(destination, filename)
                    logger.debug(f'Writing {output}')
                    with open(output, 'wb') as f:
                        f.write(item.read_random(0, item.info.meta.size))
                    extracted.append(filename)
        return extracted


class ExtPytskFile(pytsk3.File):
    """Extends pytsk3.File to also support read()

    Attributes:
        offset (int): Current offset in file
        pytsk_handle: Handle to the file
    """

    def __init__(self, pytsk_handle):
        self.pytsk_handle = pytsk_handle
        self.offset = 0

    def __bool__(self):
        return bool(self.pytsk_handle)

    def read(self, size):
        """Read bytes from file

        Args:
            size (int): Number of bytes to read

        Returns:
            bytes
        """
        return self.pytsk_handle.read_random(self.offset, size)

    def get_size(self):
        """Get size of file

        Returns:
            int: Filesize in bytes
        """
        return self.pytsk_handle.info.meta.size

    def seek(self, offset, *whence):
        """Seek to offset in file

        Args:
            offset (int): Seek to offset
            *whence: The whence argument is optional and defaults to
                os.SEEK_SET or 0 (absolute file positioning); other values are
                os.SEEK_CUR or 1 (seek relative to the current position) and
                os.SEEK_END or 2 (seek relative to the file’s end).
        """
        try:
            whence = whence[0]
            if whence == os.SEEK_CUR:
                self.offset += offset
            elif whence == os.SEEK_END:
                self.offset = self.get_size() - offset
            else:
                self.offset = offset
        except IndexError:
            self.offset = offset
