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


def get_text_image(text, image, font_filename, font_color=Color('black'), background_color=Color('#FFFFFF80')):
    padding_size = (5, 3)

    if font_color == Color('black'):
        padding_size = (0, 0)

    draw = Drawing()
    draw.fill_color = font_color
    draw.font = os.path.join('input', 'fonts', font_filename)
    draw.font_size = 18
    res_image = Image(width=int(draw.get_font_metrics(image, text, multiline=True).text_width + 2 * padding_size[0]),
                    height=int(draw.get_font_metrics(image, text, multiline=True).text_height + 2 * padding_size[1]),
                    background=background_color)
    res_image.virtual_pixel = 'transparent'
    draw.text(padding_size[0], 14 + padding_size[1], text)
    draw(res_image)
    return res_image
