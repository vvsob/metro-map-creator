from wand.image import Image
from wand.color import Color
from enum import Enum


class Orientation(Enum):
    RIGHT = 0
    DOWN = 90
    LEFT = 180
    UP = 270
    HORIZONTAL = 360
    VERTICAL = 450


def get_line(line, length, orientation):
    long_line = line.clone()
    long_line.resize(width=length)
    long_line.rotate(orientation.value)
    return long_line


class TurnType(Enum):
    RIGHT_DOWN = 0
    RIGHT_UP = 90
    DOWN_LEFT = 90
    DOWN_RIGHT = 180
    LEFT_UP = 180
    LEFT_DOWN = 270
    UP_RIGHT = 270
    UP_LEFT = 0


def get_arc(line, turn):
    arc = line.clone()
    arc.virtual_pixel = 'transparent'
    arc.resize(line.height * 5, arc.height + 1)
    arc.distort('arc', (90, 45))

    res_image = Image(height=arc.height + 3, width=arc.width + 3)
    res_image.composite(arc, left=0, top=3)
    res_image.shave(4, 4)

    res_image.rotate(turn.value)

    return res_image


def get_end_station(line, orientation):
    end_station = Image(width=line.height, height=3*line.height)
    end_station.virtual_pixel = 'transparent'

    for x in range(end_station.width):
        for y in range(end_station.height):
            if y <= line.height // 2:
                dist = min(y, x, line.height - 1 - x)
            elif y >= end_station.height - 1 - line.height // 2:
                dist = min(end_station.height - 1 - y, x, line.height - 1 - x)
            else:
                if x >= line.height // 2:
                    dist = line.height - 1 - x
                else:
                    dist = line.height // 2 - min(line.height // 2 - x, abs(y - end_station.height // 2))

            end_station[x, y] = line[0, dist]

    end_station.rotate(orientation.value)

    return end_station


def get_station(line, orientation):
    station = Image(width=2*line.height, height=line.height)
    station.virtual_pixel = 'transparent'

    for x in range(station.width):
        for y in range(station.height):
            if x <= line.height // 2:
                dist = line.height // 2 - abs(station.height // 2 - x)
            elif x < line.height:
                dist = line.height // 2 - min(x - station.height // 2, abs(y - station.height // 2))
            else:
                dist = min(y, line.height - 1 - y, station.width - 1 - x)

            station[x, y] = line[0, dist]

    station.rotate(orientation.value)

    return station


def get_transfer(line, line_type, orientation):
    transfer = line.clone()
    transfer.virtual_pixel = 'transparent'
    if line_type == 'metro':
        transfer.resize(64, transfer.height)
        transfer.distort('arc', (360, 0))
        transfer.resize(27, 27)
    if line_type == 'mcd':
        transfer.resize(44, transfer.height + 1)
        transfer.distort('arc', (360, 0))
        transfer.resize(29, 29)

    base = Image(width=transfer.width, height=transfer.height)
    for x in range(base.width):
        for y in range(base.height):
            if (x - base.width // 2)**2 + (y - base.height // 2)**2 <= 9**2:
                base[x, y] = Color('#FFFFFF')

    base.composite(transfer)

    line_part = line.clone()
    line_part.resize(width=3)
    line_part_base = Image(width=6, height=line.height)
    line_part_base.virtual_pixel = 'transparent'
    line_part_base.composite(line_part)

    for i in range(line_part_base.height):
        if 3 <= i < 6:
            line_part_base[3, i] = line[0, i]
            line_part_base[4, i] = line[0, i]
            line_part_base[5, i] = line[0, i]

    if orientation.name in [Orientation.HORIZONTAL.name, Orientation.VERTICAL.name]:
        base.composite(line_part_base, top=(base.height-line.height)//2)
    line_part_base.flop()
    base.composite(line_part_base, left=base.width-line_part_base.width, top=(base.height-line.height)//2)

    base.rotate(orientation.value)

    return base
