import os
from enum import Enum

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image


class RelativeTo(Enum):
    TOP_LEFT = 0
    LEFT = 1
    UP = 2
    RIGHT = 3
    DOWN = 4
    CENTER = 5
    LEFT_DOWN = 6


class Direction(Enum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3


def place(image, image_to_place, coords, relative_to):
    coords = list(coords)
    half_size = (image_to_place.width // 2, image_to_place.height // 2)
    if relative_to == RelativeTo.LEFT_DOWN:
        coords[1] -= image_to_place.height - 1
    if relative_to in [RelativeTo.LEFT, RelativeTo.RIGHT]:
        coords[1] -= half_size[1]
        if relative_to == RelativeTo.RIGHT:
            coords[0] -= image_to_place.width - 1
    if relative_to in [RelativeTo.UP, RelativeTo.DOWN]:
        coords[0] -= half_size[0]
        if relative_to == RelativeTo.DOWN or relative_to == RelativeTo.LEFT_DOWN:
            coords[1] -= image_to_place.height - 1
    if relative_to == RelativeTo.CENTER:
        coords[0] -= half_size[0]
        coords[1] -= half_size[1]

    image.composite(image_to_place, left=coords[0], top=coords[1])
    return [coords[0] + half_size[0], coords[1] + half_size[1]]


def turn(direction, clockwise):
    directions = ['LEFT', 'UP', 'RIGHT', 'DOWN']
    for (num, cur_direction) in enumerate(directions):
        if cur_direction == direction:
            return directions[(num + 1) % len(directions)] if clockwise else \
                directions[(num + len(directions) - 1) % len(directions)]
    raise Exception('No such direction found')


def opposite(direction):
    return turn(turn(direction, True), True)


def move(coords, delta, direction):
    res_coords = list(coords)
    if direction == Direction.LEFT:
        res_coords[0] -= delta
    elif direction == Direction.UP:
        res_coords[1] -= delta
    elif direction == Direction.RIGHT:
        res_coords[0] += delta
    else:
        res_coords[1] += delta
    return tuple(res_coords)


def move_by_image(coords, image, direction):
    if direction in ['left', 'right']:
        return move(coords, image.width, Direction[direction.upper()])
    else:
        return move(coords, image.height, Direction[direction.upper()])


def get_text_image(text, image, font_path, font_color=Color('black'), background_color=Color('#FFFFFF80')):
    padding_size = (5, 3)

    if font_color == Color('black'):
        padding_size = (0, 0)

    draw = Drawing()
    draw.fill_color = font_color
    draw.font = font_path
    draw.font_size = 18
    res_image = Image(width=int(draw.get_font_metrics(image, text, multiline=True).text_width + 2 * padding_size[0]),
                      height=int(draw.get_font_metrics(image, text, multiline=True).text_height + 2 * padding_size[1]),
                      background=background_color)
    res_image.virtual_pixel = 'transparent'
    draw.text(padding_size[0], 14 + padding_size[1], text)
    draw(res_image)
    return res_image


def get_arrow_image(size, color=Color('black'), background=Color('white')):
    image = Image(width=size, height=size, background=background)

    with Drawing() as draw:
        draw.stroke_color = color
        draw.stroke_width = 4
        draw.line((4, size // 2), (size - 1, size // 2))
        draw.draw(image)
        draw.line((2, size // 2 + 1), (size // 2, 2 + 1))
        draw.draw(image)
        draw.line((2, size // 2 - 1), (size // 2, size - 1 - 2 - 1))
        draw.draw(image)

    return image


def get_direction_image(logo_image, last_station_name, font_path, reverse_direction=False):
    last_station_name_image = get_text_image(last_station_name, logo_image, font_path)
    image_width = 20 + 27 + 10 + logo_image.width + 10 + last_station_name_image.width + 20

    direction_image = Image(width=image_width, height=128, background=Color('white'))

    cur_pos = 20
    if not reverse_direction:
        place(direction_image, get_arrow_image(27), (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += get_arrow_image(27).width + 10
        place(direction_image, logo_image, (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += logo_image.width + 10
        place(direction_image, last_station_name_image, (cur_pos, 64), RelativeTo.LEFT)

        with Drawing() as draw:
            draw.stroke_color = Color('gray')
            draw.line((image_width - 1, 10), (image_width - 1, 118))
            draw.draw(direction_image)
    else:
        with Drawing() as draw:
            draw.stroke_color = Color('gray')
            draw.line((0, 10), (0, 118))
            draw.draw(direction_image)

        place(direction_image, last_station_name_image, (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += last_station_name_image.width + 10
        place(direction_image, logo_image, (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += logo_image.width + 10
        arrow_image = get_arrow_image(27)
        arrow_image.flop()
        place(direction_image, arrow_image, (cur_pos, 64), RelativeTo.LEFT)

    return direction_image


def round_corner(image, radius, coords, positive_dx, positive_dy):
    for x in (range(coords[0], coords[0] + radius + 1) if positive_dx else range(coords[0] - radius, coords[0] + 1)):
        for y in (range(coords[1], coords[1] + radius + 1) if positive_dy else range(coords[1] - radius,
                                                                                     coords[1] + 1)):
            if (x - coords[0]) ** 2 + (y - coords[1]) ** 2 > radius ** 2:
                image[x, y] = Color('#FFFFFF00')


def round_corners(image, radius):
    round_corner(image, radius, (radius, radius), False, False)
    round_corner(image, radius, (image.width - 1 - radius, radius), True, False)
    round_corner(image, radius, (radius, image.height - 1 - radius), False, True)
    round_corner(image, radius, (image.width - 1 - radius, image.height - 1 - radius), True, True)


def complete_width(image):
    map_width = image.width
    total_width = (map_width + 128 - 1) // 128 * 128
    if total_width // 128 % 2 == 0:
        total_width += 128

    formatted_image = Image(width=total_width, height=128, background=Color('#FFFFFF00'))
    formatted_image.composite(image, left=(total_width - map_width) // 2)
    return formatted_image
