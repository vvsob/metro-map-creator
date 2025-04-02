import argparse
import logging
import pathlib

from transliterate import translit

import datetime
import json
import os

from map_data import MapData, Station


def format_filename(filename):
    return translit(filename.replace(" ", "_").replace("\n", "_"), "ru", reversed=True)


def draw_full_map(args):
    map_data = MapData(json.loads(args.map_data.read()), args.assets)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    metro_map = map_data.draw()
    metro_map.save(filename=args.output)


def draw_linear_map(args):
    map_data = MapData(json.loads(args.map_data.read()), args.assets)

    if args.all:
        lines = map_data.lines
    else:
        lines = [line for line in map_data.lines if line.name in args.lines]

    if not lines:
        print("No lines to render")
        return

    os.makedirs(args.output, exist_ok=True)

    for i, line in enumerate(lines):
        logging.info(f"[{i + 1} / {len(lines)}] Rendering {line.name}")
        for element in line.elements:
            if isinstance(element, Station):
                for reverse_direction in [0, 1]:
                    linear_metro_map = line.get_linear_metro_map(
                        reverse_direction, element.name
                    )

                    linear_metro_map.save(
                        filename=os.path.join(
                            args.output,
                            format_filename(
                                "linear_"
                                + line.name
                                + "_"
                                + element.name
                                + "_"
                                + str(reverse_direction)
                                + ".png"
                            ),
                        )
                    )

    print(f"Rendered {len(lines)} lines")


def draw_station_sign(args):
    map_data = MapData(json.loads(args.map_data.read()), args.assets)

    if args.all_lines:
        lines = map_data.lines
    else:
        lines = [line for line in map_data.lines if line.name in args.lines]

    for i, line in enumerate(lines):
        for element in line.elements:
            if isinstance(element, Station):
                if not args.all_stations and element.name not in args.stations:
                    continue
                station_sign = element.get_sign_image()
                station_sign.save(
                        filename=os.path.join(
                            args.output,
                            format_filename(
                                "sign_"
                                + line.name
                                + "_"
                                + element.name
                                + ".png"
                            ),
                        )
                    )



def main():
    parser = argparse.ArgumentParser(
        prog="metro-map-creator",
        description="a tool for creating metro maps using json data",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("map_data", type=argparse.FileType("r"))
    parent_parser.add_argument(
        "assets", type=pathlib.Path, help="path to the asset folder"
    )
    parent_parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="verbosity"
    )

    full_parser = subparsers.add_parser(
        "full", parents=[parent_parser], help="Draw the complete metro map"
    )
    full_parser.add_argument(
        "-o",
        "--output",
        default="./output/metro_map.png",
        type=str,
        help="name of the output file",
    )
    full_parser.set_defaults(func=draw_full_map)

    linear_parser = subparsers.add_parser(
        "linear", parents=[parent_parser], help="Draw the linear map for a station"
    )
    linear_parser.add_argument(
        "-l",
        "--lines",
        action="extend",
        nargs="+",
        default=[],
        help="name of the lines to be drawn",
    )
    linear_parser.add_argument("--all", action="store_true", help="render all lines")
    linear_parser.add_argument(
        "-o",
        "--output",
        default="./output",
        type=pathlib.Path,
        help="name of the output folder",
    )
    linear_parser.set_defaults(func=draw_linear_map)

    station_parser = subparsers.add_parser(
        "station", parents=[parent_parser], help='Draw the station entrance sign'
    )
    station_parser.add_argument(
        "-l",
        "--lines",
        action="extend",
        nargs="+",
        default=[],
        help="select the lines to be drawn",
    )
    station_parser.add_argument("--all_lines", action="store_true", help="select all lines")

    station_parser.add_argument(
        "-s",
        "--stations",
        action="extend",
        nargs="+",
        default=[],
        help="select the stations to be drawn",
    )
    station_parser.add_argument("--all_stations", action="store_true", help="render all stations on selected lines")
    station_parser.add_argument(
        "-o",
        "--output",
        default="./output",
        type=pathlib.Path,
        help="name of the output folder",
    )
    station_parser.set_defaults(func=draw_station_sign)

    args = parser.parse_args()

    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.datetime.now()

    args.func(args)

    print(
        f"Generating completed in {int((datetime.datetime.now() - start_time).total_seconds() * 1000)} ms"
    )


if __name__ == "__main__":
    main()
