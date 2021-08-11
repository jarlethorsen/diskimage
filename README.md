## About The Project

A python module that lets you handle disk images in an easy way.

## Installation

`pip install diskimage`

## Usage
The tool comes with a commandline client `di` that will let you work with diskimages:

```
usage: di <command> <options> disk-image-file

Get information from disk-images.

positional arguments:
  disk_image

optional arguments:
  -h, --help         show this help message and exit
  -v, --verbose      Add verbosity, -vv to enable debugging
  --version VERSION  Print version information
```

or

You can also use the available python methods directly from your script:

```python
>>> import diskimage as di

>>> image = di.DiskImage.from_file('split.E01')

>>> image.filesystems
[<diskimage.filesystem.FileSystem object at 0x741564ba8580>, <diskimage.filesystem.FileSystem object at 0x741564ba8100>]

>>> [item.name for item in image.get_items()]
['$AttrDef', '$BadClus', '$Bitmap', '$Boot', '$Extend', '$ObjId', '$Quota', '$Reparse', '$LogFile', '$MFT', '$MFTMirr', '$Secure', '$UpCase', '$Volume', 'secret.txt', '$OrphanFiles', '$AttrDef', '$BadClus', '$Bitmap', '$Boot', '$Extend', '$ObjId', '$Quota', '$Reparse', '$LogFile', '$MFT', '$MFTMirr', '$Secure', '$UpCase', '$Volume', 'secret.txt', '$OrphanFiles']
```

## License

Distributed under the MIT License. See `LICENSE` for more information.


## Contact

Jarle Thorsen - [@jarlethorsen](https://twitter.com/jarlethorsen) - jarlethorsen@gmail.com

Project Link: [https://github.com/jarlethorsen/diskimage](https://github.com/jarlethorsen/diskimage)
