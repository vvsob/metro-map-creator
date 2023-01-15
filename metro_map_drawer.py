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
                if element.full_name() == highlighted_station:
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

    def draw_transfer(self, metro_map_image, transfer):
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

    # def get_linear_metro_map(self, natural_direction, line_name, station_name=None):
    #     station_line = self.map_data.get_line(line_name)
    #
    #     stations = list(station_line['elements'])
    #     station_line['elements'].clear()
    #
    #     if not natural_direction:
    #         stations = reversed(stations)
    #
    #     is_first_station = True
    #     for (num, element) in enumerate(stations):
    #         if element['type'] == 'station' and ('planned' not in element or not element['planned']):
    #             if start_station_name[1] == element['name']:
    #                 stations = stations[num:]
    #                 break
    #             is_first_station = False
    #
    #     stations = [element for element in stations if element['type'] == 'station']
    #
    #     metro_map_image = Image(height=128, width=2048, background=Color('white'))
    #
    #     station_line['start'] = [2048 - 64, 60]
    #     station_line['direction'] = 'left'
    #     for (num, station) in enumerate(stations):
    #         station['orientation'] = 'up'
    #         if not MetroMapDrawer.is_transfer(self.map_data.transfers'], (station_line['name'], station['name'])):
    #             station['name_offset'] = [0, -17]
    #             station['name_relative_to'] = 'down'
    #         else:
    #             station['name_offset'] = [-10, -17]
    #             station['name_relative_to'] = 'left_down'
    #         station['hide_name'] = False
    #         if not (num == 0 and is_first_station):
    #             station_line['elements'].append({'type': 'line', 'length': 150})
    #         station_line['elements'].append(station)
    #
    #     stations_centers = MetroMapDrawer.draw_line(station_line, self.map_data.transfers'], metro_map_image)
    #     MetroMapDrawer.draw_line_stations_names(metro_map_image, station_line, stations_centers,
    #                                             self.map_data.font_filename'], start_station_name)
    #
    #     for station in stations:
    #         station_name = (station_line['name'], station['name'])
    #         if MetroMapDrawer.is_transfer(self.map_data.transfers'], station_name):
    #             place(metro_map_image, MetroMapDrawer.get_logo_image(station_line),
    #                   [stations_centers[station_name][0], stations_centers[station_name][1] + 30], RelativeTo.CENTER)
    #
    #     return metro_map_image
