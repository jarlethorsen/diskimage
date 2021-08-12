#!/usr/bin/env python3
import argparse
import os
import sys
import diskimage


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s <command> <options> diskimagefile",
        description="Get information from disk-images."
    )

    parser.add_argument('-v', '--verbose', help='Add verbosity, -vv to enable debugging', action='count', default=0)
    parser.add_argument('--version', help='Print version information')
    parser.add_argument('diskimagefile', nargs='?')
    return parser


def print_info(diskimage_file):
    image = diskimage.DiskImage.from_file(diskimage_file)
    if image:
        if image.filesystems:
            print('[*] Filesystems found:')
            for i, filesystem in enumerate(image.filesystems):
                print(f'{i}. offset={filesystem.offset} filesystem={filesystem.fstype}')
        else:
            print(f'Found no supported filesystems in this diskimage.')
    else:
        print(f'*ERROR* File {diskimage_file} is not a supported diskimage')


def main():
    parser = init_argparse()
    args = parser.parse_args()
    diskimage_file = args.diskimagefile
    if diskimage_file is None:
        print(f'diskimage v{diskimage.__version__}')
        parser.print_help()
        sys.exit(0)

    if os.path.isfile(diskimage_file):
        print_info(diskimage_file)
    else:
        print(f'ERROR! diskimage {diskimage_file} does not exist!\nPlease provide a diskimage as input')
        parser.print_help()


if __name__ == '__main__':
    main()
