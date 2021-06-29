import pytsk3


class Item:
    """A class for any item in a FileSystem

    Attributes:
        filesystem (FileSystem): The diskimage.FileSystem Object this diskimage.Item is a part of
        inode (int): The inode of the item
        name (string): The name of the item
        parents (list): A list of any parents this Item belongs to. We use this
            to keep track of where the items belong in the hierarchy, as it may
            be several levels down when using recursive listing
        path (string): The path where item is located
        type (string): Type of item
    """

    def __init__(self):
        self.name = None
        self.path = None
        self.type = None
        self.inode = None
        self.parents = []
        self.filesystem = None

    @staticmethod
    def from_pytsk_item(filesystem, path, item):
        """Returns an diskimage.Item Object from a pytsk item

        Args:
            filesystem (FileSystem): the diskimage.FileSystem object the diskimage.Item belongs to
            path (string): The path where the item is located
            item (pytsk.Item): The pytsk item to handle

        Returns:
            diskimage.Item object representing the pytsk item
        """
        i = Item()
        i.filesystem = filesystem
        i.path = path
        i.name = item.info.name.name.decode('utf-8')
        if item.info.meta:
            if item.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
                i.type = 'dir'
            i.inode = item.info.meta.addr
        else:
            # If item has no meta-info we just skip it, and return None
            i = None
        return i

    def open(self):
        """Open the file

        Tries to open the file and returns a file handle to it

        Returns:
            filehandle, or None if it is not able to open the file
        """
        return self.filesystem.get_file_handle(inode=self.inode)
