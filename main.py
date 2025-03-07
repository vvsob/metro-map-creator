import argparse
import logging
import pathlib

from transliterate import translit

import datetime
import json
import os

from map_data import MapData, Station


def format_filename(filename):
    return translit(filename.replace(' ', '_').replace('\n', '_'), "ru", reversed=True)


def draw_full_map(args):
    map_data = MapData(json.loads(args.map_data.read()), args.assets)

    if not os.path.exists('output'):
        os.mkdir('output')
    for file in os.listdir('output'):
        os.remove(os.path.join('output', file))

    metro_map = map_data.draw()
    metro_map.save(filename=args.output.name)


def draw_linear_map(args):
    map_data = MapData(json.loads(args.map_data.read()), args.assets)

    if args.all:
        lines = map_data.lines
    else:
        lines = [l for l in map_data.lines if l.name in args.lines]

    if not lines:
        print("No lines to render")
        return

    for i, line in enumerate(lines):
        logging.info(f"[{i + 1} / {len(lines)}] Rendering {line.name}")
        is_bidirectional = line.name in ['Первый диаметр', 'Второй диаметр', 'Филёвская']
        for element in line.elements:
            if isinstance(element, Station):
                for reverse_direction in [0, 1]:
                    linear_metro_map = line.get_linear_metro_map(reverse_direction, element.name, is_bidirectional)

                    linear_metro_map.save(filename=os.path.join('output', format_filename('linear_' + line.name + '_' +
                                                                                          element.name + '_' +
                                                                                          str(reverse_direction) + '.png')))

    print(f"Rendered {len(lines)} lines")


def main():
    parser = argparse.ArgumentParser(
        prog="metro-map-creator",
        description="a tool for creating metro maps using json data"
    )

    subparsers = parser.add_subparsers(dest='command', help="Available commands", required=True)

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('map_data', type=argparse.FileType('r'))
    parent_parser.add_argument('assets', type=pathlib.Path, help="path to the asset folder")
    parent_parser.add_argument('-v', "--verbose", action='count', default=0, help="verbosity")

    full_parser = subparsers.add_parser('full', parents=[parent_parser], help="Draw the complete metro map")
    full_parser.add_argument('-o', '--output', default='./metro_map.png', type=argparse.FileType('w'),
                             help="name of the output file")
    full_parser.set_defaults(func=draw_full_map)

    linear_parser = subparsers.add_parser('linear', parents=[parent_parser], help="Draw the linear map for a station")
    linear_parser.add_argument('-l', '--lines', action='extend', nargs='+', default=[],
                               help="name of the lines to be drawn")
    linear_parser.add_argument('--all', action='store_true', help="render all lines")
    linear_parser.add_argument('-o', '--output', default="./output", type=pathlib.Path,
                               help="name of the output folder")
    linear_parser.set_defaults(func=draw_linear_map)

    args = parser.parse_args()

    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.datetime.now()

    args.func(args)

    print(f'Generating completed in {int((datetime.datetime.now() - start_time).total_seconds() * 1000)} ms')


if __name__ == "__main__":
    main()
