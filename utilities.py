from enum import Enum


class RelativeTo(Enum):
    TOP_LEFT = 0
    LEFT = 1
    UP = 2
    RIGHT = 3
    DOWN = 4
    CENTER = 5


class Direction(Enum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3


def place(img, img_to_place, coords, relative_to):
    coords = coords.copy()
    half_size = (img_to_place.width // 2, img_to_place.height // 2)
    if relative_to in [RelativeTo.LEFT, RelativeTo.RIGHT]:
        coords[1] -= half_size[1]
        if relative_to == RelativeTo.RIGHT:
            coords[0] -= img_to_place.width - 1
    elif relative_to in [RelativeTo.UP, RelativeTo.DOWN]:
        coords[0] -= half_size[0]
        if relative_to == RelativeTo.DOWN:
            coords[1] -= img_to_place.height - 1
    elif relative_to == RelativeTo.CENTER:
        coords[0] -= half_size[0]
        coords[1] -= half_size[1]

    img.composite(img_to_place, left=coords[0], top=coords[1])
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
    if direction == Direction.LEFT:
        coords[0] -= delta
    elif direction == Direction.UP:
        coords[1] -= delta
    elif direction == Direction.RIGHT:
        coords[0] += delta
    else:
        coords[1] += delta


def move_by_img(coords, img, direction):
    if direction in ['left', 'right']:
        return move(coords, img.width, Direction[direction.upper()])
    else:
        return move(coords, img.height, Direction[direction.upper()])
