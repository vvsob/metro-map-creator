import copy

from draw_elements import *
from utilities import *
from functools import cmp_to_key
from map_data import MapData, LineSegment, Turn, Station


def cmp(line1, line2):
    return line1.priority - line2.priority


class MetroMapDrawer:
    def __init__(self, json):
        self.map_data = MapData(json)

    @staticmethod
    def continue_line(coords, image, line_image, delta, direction):
        line_part = line_image.clone()
        line_part.resize(delta, line_part.height)
        if direction in ['up', 'down']:
            line_part.rotate(90)
        place(image, line_part, coords, RelativeTo[opposite(direction.upper())])
        return move(coords, delta, Direction[direction.upper()])

    @staticmethod
    def continue_with_first_station(metro_map_image, station, position, direction, station_image):
        if not station.is_transfer():
            end_station = get_end_station(station_image, Orientation[opposite(direction.upper())])
        else:
            end_station = get_transfer(station_image, station.line.type, Orientation[direction.upper()])

        place(metro_map_image, end_station, position, RelativeTo.CENTER)

        if not station.is_transfer():
            position = move(position, station_image.height // 2 + 1, Direction[direction.upper()])
        else:
            position = move(position, end_station.height // 2 + 1, Direction[direction.upper()])

        return position

    @staticmethod
    def continue_with_station(metro_map_image, station, position, direction, line_image):
        image_pos = tuple(position)

        if not station.is_transfer():
            station_image = get_station(line_image, Orientation[station.orientation.upper()])
            image_pos = move(image_pos, line_image.height // 2 + (station.orientation in ['right', 'down']),
                             Direction[station.orientation.upper()])
        else:
            orientation = Orientation.HORIZONTAL
            if direction in ['up', 'down']:
                orientation = Orientation.VERTICAL
            station_image = get_transfer(line_image, station.line.type, orientation)

        place(metro_map_image, station_image, image_pos, RelativeTo[opposite(direction.upper())])
        return move_by_image(position, station_image, direction)

    @staticmethod
    def continue_with_last_station(metro_map_image, station, position, direction, station_image):
        if not station.is_transfer():
            end_station = get_end_station(station_image, Orientation[direction.upper()])
        else:
            end_station = get_transfer(station_image, station.line.type, Orientation[opposite(direction.upper())])

        place(metro_map_image, end_station, position, RelativeTo[opposite(direction.upper())])

    @staticmethod
    def continue_with_turn(metro_map_image, turn, position, direction, turn_image):
        arc = get_arc(turn_image, TurnType[direction.upper() + '_' + turn.direction.upper()])
        image_pos = list(position)
        if direction == 'right':
            if turn.direction == 'down':
                image_pos[1] += -(turn_image.height // 2)
            else:
                image_pos[1] += -(turn_image.height // 2) - arc.height + turn_image.height
        if direction == 'down':
            if turn.direction == 'left':
                image_pos[0] += -(turn_image.height // 2) + turn_image.height - arc.width
            else:
                image_pos[0] += -(turn_image.height // 2)
        if direction == 'left':
            image_pos[0] += -arc.width + 1
            if turn.direction == 'up':
                image_pos[1] += -(turn_image.height // 2) - arc.height + turn_image.height
            else:
                image_pos[1] += -(turn_image.height // 2)
        if direction == 'up':
            image_pos[1] += -arc.width + 1
            if turn.direction == 'right':
                image_pos[0] += -(turn_image.height // 2)
            else:
                image_pos[0] += -(turn_image.height // 2) + turn_image.height - arc.width

        place(metro_map_image, arc, image_pos, RelativeTo.TOP_LEFT)

        position = move(position, arc.height - turn_image.height // 2 - 1, Direction[direction.upper()])
        direction = turn.direction
        position = move(position, arc.height - turn_image.height // 2, Direction[direction.upper()])

        return position, direction

    @staticmethod
    def draw_station_name(metro_map_image, station, font_filename, highlight_color=None):
        if not station.hide_name:
            if highlight_color is None:
                text_image = get_text_image(station.name, metro_map_image, font_filename)
            else:
                text_image = get_text_image(station.name, metro_map_image, font_filename,
                                            Color('white'), highlight_color)

            place(metro_map_image, text_image, (station.position[0] + station.name_offset[0],
                                                station.position[1] + station.name_offset[1]),
                  RelativeTo[station.name_relative_to.upper()])

    @staticmethod
    def draw_line_stations_names(metro_map_image, line, font_filename, highlighted_station):
        for element in line.elements:
            if isinstance(element, Station):
                highlight_color = None
                if element == highlighted_station:
                    highlight_color = line.line_image[0, 0]
                MetroMapDrawer.draw_station_name(metro_map_image, element, font_filename, highlight_color)

    @staticmethod
    def draw_line(line, metro_map_image):
        position = line.start
        direction = line.direction

        line_width = line.line_image.height
        station_length = get_station(line.line_image, Orientation.UP).width
        transfer_length = get_transfer(line.line_image, line.type, Orientation.RIGHT).width
        turn_length = get_arc(line.line_image, TurnType.RIGHT_DOWN).width

        for (num, element) in enumerate(line.elements):
            element_image = line.planned_line_image if element.is_actually_planned() else line.line_image

            if isinstance(element, LineSegment):
                line_length = element.length

                if num != 0:
                    prev_element = line.elements[num - 1]
                    if isinstance(prev_element, Station):
                        line_length -= station_length // 2 + 1 if not \
                            prev_element.is_transfer() else transfer_length // 2 + 1
                    elif isinstance(prev_element, Turn):
                        line_length -= turn_length - line_width // 2

                if num != len(line.elements) - 1:
                    next_element = line.elements[num + 1]
                    if isinstance(next_element, Station):
                        line_length -= station_length // 2 if not next_element.is_transfer() else transfer_length // 2
                    elif isinstance(next_element, Turn):
                        line_length -= turn_length - line_width // 2 - 1

                if line_length < 0:
                    raise Exception('Line segment is too short')

                position = MetroMapDrawer.continue_line(position, metro_map_image, element_image, line_length,
                                                        direction)

            if isinstance(element, Station):
                if num == 0:
                    position = MetroMapDrawer.continue_with_first_station(metro_map_image, element,
                                                                          position, direction, element_image)
                elif num != len(line.elements) - 1:
                    position = MetroMapDrawer.continue_with_station(metro_map_image, element,
                                                                    position, direction, element_image)
                else:
                    MetroMapDrawer.continue_with_last_station(metro_map_image, element,
                                                              position, direction, element_image)

            if isinstance(element, Turn):
                position, direction = MetroMapDrawer.continue_with_turn(metro_map_image, element, position, direction,
                                                                        element_image)

    @staticmethod
    def draw_logos(metro_map_image, line):
        if isinstance(line.elements[0], Station):
            first_station_center = line.elements[0].position
            if line.start_logo_offset is not None:
                place(metro_map_image, line.logo_image,
                      [first_station_center[0] + line.start_logo_offset[0],
                       first_station_center[1] + line.start_logo_offset[1]],
                      RelativeTo.CENTER)

        if isinstance(line.elements[len(line.elements) - 1], Station):
            last_station_center = line.elements[len(line.elements) - 1].position
            if line.end_logo_offset[0] is not None:
                place(metro_map_image, line.logo_image,
                      [last_station_center[0] + line.end_logo_offset[0],
                       last_station_center[1] + line.end_logo_offset[1]],
                      RelativeTo.CENTER)

    def get_max_text_length(self, metro_map_image):
        max_text_length = 0
        for line in self.map_data.lines:
            if line.name is not None:
                max_text_length = max(max_text_length,
                                      get_text_image(line.name, metro_map_image, self.map_data.font_filename).width)
        return max_text_length

    def draw_lines_info(self, metro_map_image):
        lines_image = Image(width=400 + self.get_max_text_length(metro_map_image),
                            height=len(self.map_data.lines) * 40)
        cur_top = 0
        for line in self.map_data.lines:
            place(lines_image, line.logo_image, [30, cur_top + 20], RelativeTo.CENTER)

            line.line_image.resize(width=100)
            place(lines_image, line.line_image, [70, cur_top + 20], RelativeTo.LEFT)

            place(lines_image, get_text_image(line.name, metro_map_image, self.map_data.font_filename),
                  [190, cur_top + 20], RelativeTo.LEFT)

            cur_top += 40

        metro_map_image.composite(lines_image, left=25, top=metro_map_image.height - lines_image.height - 20)

    def draw_info(self, metro_map_image):
        metro_map_image.composite(self.map_data.info_image, left=metro_map_image.width - self.map_data.info_image.width,
                                  top=metro_map_image.height - self.map_data.info_image.height)

    @staticmethod
    def draw_transfer(metro_map_image, transfer):
        def add(point1, point2):
            return point1[0] + point2[0], point1[1] + point2[1]

        def sub(point1, point2):
            return add(point1, (-point2[0], -point2[1]))

        def mult(point, number):
            return point[0] * number, point[1] * number

        def length(point):
            return (point[0] ** 2 + point[1] ** 2) ** 0.5

        def move_point(point, to_point, delta):
            dv = sub(to_point, point)
            dv = mult(dv, delta / length(dv))
            return add(point, dv)

        line1 = transfer.stations[0].line
        line2 = transfer.stations[1].line
        color1 = line1.line_image[0, 0]
        color2 = line2.line_image[0, 0]
        mcd1 = line1.type == 'mcd'
        mcd2 = line2.type == 'mcd'

        coords1 = transfer.stations[0].position
        coords2 = transfer.stations[1].position
        mid = mult(add(coords1, coords2), 0.5)

        if transfer.is_direct:
            moved_coords1 = move_point(coords1, mid, 10)
            moved_coords2 = move_point(coords2, mid, 10)

            with Drawing() as draw:
                draw.stroke_color = color1
                draw.stroke_width = 9
                draw.line(moved_coords1, mid)
                draw(metro_map_image)

            with Drawing() as draw:
                draw.stroke_color = color2
                draw.stroke_width = 9
                draw.line(moved_coords2, mid)
                draw(metro_map_image)

            with Drawing() as draw:
                draw.stroke_color = Color('white')
                draw.stroke_width = 3
                if mcd1:
                    coords1 = move_point(coords1, mid, 7)
                if mcd2:
                    coords2 = move_point(coords2, mid, 7)
                draw.line(coords1, coords2)
                draw(metro_map_image)
        else:
            moved_coords1 = move_point(coords1, mid, 12.5 + mcd1)
            moved_coords2 = move_point(coords2, mid, 12.5 + mcd2)

            dist = length(sub(moved_coords1, moved_coords2))
            count = max(2, int(round(dist) / 6 + 0.5))

            step = dist / count

            cur_coord = move_point(moved_coords1, moved_coords2, (dist - step * (count - 2)) / 2)

            for i in range(count - 1):
                with Drawing() as draw:
                    draw.stroke_color = Color('rgb(134, 164, 193)')
                    draw.fill_color = draw.stroke_color
                    draw.circle(cur_coord, add(cur_coord, (0.75, 0)))
                    draw(metro_map_image)
                    cur_coord = move_point(cur_coord, moved_coords2, step)

    def get_metro_map(self, highlighted_station=None):
        metro_map_image = Image(height=self.map_data.image_resolution[0],
                                width=self.map_data.image_resolution[1], background=Color('white'))

        for line in sorted(self.map_data.lines, key=cmp_to_key(cmp)):
            self.draw_line(line, metro_map_image)

        for line in self.map_data.lines:
            self.draw_logos(metro_map_image, line)

        for transfer in self.map_data.transfers:
            self.draw_transfer(metro_map_image, transfer)

        for line in self.map_data.lines:
            self.draw_line_stations_names(metro_map_image, line, self.map_data.font_filename, highlighted_station)

        self.draw_lines_info(metro_map_image)

        self.draw_info(metro_map_image)

        return metro_map_image

    def get_linear_metro_map(self, reverse_direction, line_name, start_station_name=None):
        station_line = self.map_data.get_line(line_name)
        start_station = station_line.get_station(start_station_name)

        elements = list(station_line.elements)
        if reverse_direction:
            elements = list(reversed(elements))

        is_first_station = True
        if start_station_name is not None:
            for (num, element) in enumerate(elements):
                if isinstance(element, Station) and not element.is_actually_planned():
                    if element == start_station:
                        elements = elements[num:]
                        break
                    is_first_station = False

        stations = [element for element in elements if isinstance(element, Station)]
        for (num, station) in enumerate(stations):
            if station.is_actually_planned():
                stations = stations[:num]
                break

        if len(stations) <= 1:
            return self.map_data.no_boarding_image

        temp_image = Image(width=100, height=100)

        line_segments_length = []
        stations_orientation = []
        stations_transfers_length = []

        first_offset = None
        prev_station_position = None
        last_top = 0
        last_bottom = 0
        is_top = True
        for station in stations:
            if station.is_transfer() or station == stations[len(stations) - 1]:
                is_top = True

            name_length = get_text_image(station.name, temp_image, self.map_data.font_filename).width

            transfer_lines = station.get_transfer_lines()
            transfers_length = max(0, 10 * (len(transfer_lines) - 1))
            for line in transfer_lines:
                transfers_length += line.logo_image.width
            stations_transfers_length.append(transfers_length)

            if is_top:
                station_position = max(last_top + 40 + name_length // 2, last_bottom + 40 + transfers_length // 2)
                last_top = station_position + (name_length + 1) // 2
                last_bottom = station_position + (transfers_length + 1) // 2
            else:
                station_position = max(last_top + 40, last_bottom + 40 + name_length // 2)
                last_top = station_position
                last_bottom = station_position + (name_length + 1) // 2

            if first_offset is None:
                first_offset = max(last_top, last_bottom) - 20

            stations_orientation.append('up' if is_top else 'down')
            if prev_station_position is not None:
                line_segments_length.append(station_position - prev_station_position)

            prev_station_position = station_position
            is_top = not is_top

        total_width = max(last_top, last_bottom)

        last_station_name_image = get_text_image(stations[len(stations) - 1].name, temp_image,
                                                 self.map_data.font_filename)
        end_offset = 20 + 27 + 10 + station_line.logo_image.width + 10 + last_station_name_image.width + 20

        total_width += end_offset

        linear_line = copy.copy(station_line)
        linear_line.elements = list(station_line.elements)
        linear_line.elements.clear()

        if not is_first_station:
            total_width += max(first_offset // 2, 50) - first_offset // 2
            linear_line.elements.append(LineSegment(linear_line, {'length': max(first_offset // 2 + 20, 50)}))

        linear_line.start_logo_offset = None
        linear_line.end_logo_offset = None
        linear_line.direction = 'left'
        if is_first_station:
            linear_line.start = (total_width - 1 - 20 - first_offset // 2, 64)
        else:
            linear_line.start = (total_width - 1, 64)

        linear_metro_map_image = Image(width=total_width, height=128, background=Color('white'))

        for (num, station) in enumerate(stations):
            if not station.is_transfer():
                station.orientation = stations_orientation[num]
                station.name_relative_to = opposite(station.orientation.upper()).lower()
            else:
                station.name_relative_to = 'down'

            if station.orientation == 'down':
                station.name_offset = (0, 20)
            else:
                station.name_offset = (0, -20)

            station.hide_name = False

            linear_line.elements.append(station)
            if num != len(stations) - 1:
                linear_line.elements.append(LineSegment(linear_line, {'length': line_segments_length[num]}))

        linear_line.fix_stations_positions()

        for (num, station) in enumerate(stations):
            if station.is_transfer():
                cur_logo_pos = station.position[0] - stations_transfers_length[num] // 2
                for line in reversed(sorted(station.get_transfer_lines(), key=cmp_to_key(cmp))):
                    transfer_logo = line.logo_image
                    place(linear_metro_map_image, transfer_logo, (cur_logo_pos, 100), RelativeTo.LEFT)
                    cur_logo_pos += transfer_logo.width + 10

        MetroMapDrawer.draw_line(linear_line, linear_metro_map_image)
        MetroMapDrawer.draw_line_stations_names(linear_metro_map_image, linear_line,
                                                self.map_data.font_filename, start_station)

        with Drawing() as draw:
            draw.stroke_color = Color('gray')
            draw.line((end_offset, 10), (end_offset, 118))
            draw.draw(linear_metro_map_image)

        cur_pos = 20
        place(linear_metro_map_image, get_arrow_image(27), (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += get_arrow_image(27).width + 10
        place(linear_metro_map_image, linear_line.logo_image, (cur_pos, 64), RelativeTo.LEFT)
        cur_pos += linear_line.logo_image.width + 10
        place(linear_metro_map_image, last_station_name_image, (cur_pos, 64), RelativeTo.LEFT)

        round_corners(linear_metro_map_image, 10)

        return complete_width(linear_metro_map_image)
