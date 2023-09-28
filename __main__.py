import sys
import textwrap
import zlib
import struct
import os
from PIL import Image
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from pathlib import Path


def is_pcx(data: bytes) -> bool:
    size, width, height = struct.unpack('<III', data[:12])
    return size == width * height or size == width * height * 3


def read_pcx(data):
    size, width, height = struct.unpack('<III', data[:12])
    if size == width * height:
        img = Image.frombytes('P', (width, height), data[12:12 + width * height])
        palette: list = []
        for i in range(256):
            offset: int = 12 + width * height + i * 3
            r, g, b = struct.unpack('<BBB', data[offset:offset + 3])
            palette.extend((r, g, b))

        img.putpalette(palette)
        return img
    else:
        return Image.frombytes('RGB', (width, height), data[12:])


def unpack_lod(src: str, dest: str) -> None:
    with open(src, 'rb') as f:
        header: bytes = f.read(4)
        if header != b'LOD\x00':
            print(f'{src} is not LOD file')
            return

        f.seek(8)
        total, *_ = struct.unpack('<I', f.read(4))
        f.seek(92)

        files: list = []
        for _ in range(total):
            filename, *_ = struct.unpack('16s', f.read(16))
            filename = filename[:filename.index(b'\x00')].lower()
            offset, size, _, csize = struct.unpack('<IIII', f.read(16))
            files.append((filename, offset, size, csize))

        for filename, offset, size, csize in files:
            name: str = os.path.join(dest, filename.decode())
            f.seek(offset)
            if csize != 0:
                data: bytes = zlib.decompress(f.read(csize))
            else:
                data: bytes = f.read(size)

            if is_pcx(data):
                img = read_pcx(data)
                name = os.path.splitext(name)[0]
                name = name + '.png'
                img.save(name)
            else:
                with open(name, 'wb') as o:
                    o.write(data)


if __name__ == '__main__':
    parser: ArgumentParser = ArgumentParser(
        description=textwrap.dedent('''
            extract Heroes of Might and Magic 3 .lod files
            copyright © 2023 Vũ Đắc Hoàng Ân'''),
        formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument('source', help='path to .lod file')
    parser.add_argument('destination', help='path to directory which files will be extracted to')
    parser.add_argument('-v', '--version', action='version', version='1.0.0')

    args: Namespace = parser.parse_args()
    src: Path = Path(args.source)
    dest: Path = Path(args.destination)
    if not src.is_file():
        print(f'Error: file {src} not found')
        sys.exit()

    if not dest.is_dir():
        print(f'Error: {dest} is not a directory')
        sys.exit()

    unpack_lod(src, dest)
