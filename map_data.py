import logging

import transliterate

from utilities import *
from draw_elements import *

from typing import Dict, Any, List
from functools import cmp_to_key
import copy


class Element:
    def __init__(self, line: "Line", is_planned: bool):
        self.line = line
        self.is_planned = is_planned

    def is_actually_planned(self):
        num = self.line.elements.index(self)
        for slice_ in (self.line.elements[num:], self.line.elements[: num + 1]):
            for element in slice_:
                if element.is_planned is not None:
                    if element.is_planned:
                        return True
                    else:
                        break
                elif isinstance(element, Station):
                    break

        return False


class LineSegment(Element):
    def __init__(
        self, line: "Line", line_segment_json: Dict[str, Any], is_planned=None
    ):
        super().__init__(line, is_planned)
        self.line = line
        self.length = line_segment_json.get("length")
        self.is_planned = line_segment_json.get("is_planned")


class Turn(Element):
    def __init__(self, line: "Line", turn_json: Dict[str, Any], is_planned=None):
        super().__init__(line, is_planned)
        self.line = line
        self.direction = turn_json.get("direction")
        self.is_planned = turn_json.get("is_planned")


class Station(Element):
    def __init__(self, line, station_json: Dict[str, Any], position, is_planned=None):
        super().__init__(line, is_planned)
        self.line = line
        self.name = station_json.get("name")
        self.name_offset = station_json.get("name_offset")
        self.orientation = station_json.get("orientation")
        self.name_relative_to = station_json.get("name_relative_to")
        self.hide_name = station_json.get("hide_name", False)
        self.is_planned = station_json.get("is_planned")

        logging.info(
            f"Station: {self.name}\nLine: {self.line.name}\nLocation {position}"
        )

        self.position = position

        self.transfers = []

    def full_name(self):
        return self.line.name, self.name

    def is_transfer(self):
        return len(self.transfers) > 0

    def get_transfer_stations(self):
        transfer_stations = set()
        self.get_transfer_stations_rec(transfer_stations)
        transfer_stations.remove(self)
        return transfer_stations

    def get_transfer_stations_rec(self, used, indirect_limit=1):
        used.add(self)

        for transfer in self.transfers:
            another_station = (
                transfer.stations[0]
                if transfer.stations[1] == self
                else transfer.stations[1]
            )
            if another_station not in used and not (
                indirect_limit == 0 and not transfer.is_direct
            ):
                another_station.get_transfer_stations_rec(
                    used, indirect_limit - (not transfer.is_direct)
                )

    def get_transfer_lines(self):
        transfer_lines = set()
        for transfer_station in self.get_transfer_stations():
            transfer_lines.add(transfer_station.line)

        if self.line in transfer_lines:
            transfer_lines.remove(self.line)
        return transfer_lines

    def get_sign_image(self, width, height, transfer_rendering=True):
        frame_size = 4

        sign_image = Image(width=width - frame_size * 2, height=height - frame_size * 2, background=Color('white'))
        sign_image.virtual_pixel = 'transparent'

        lines = [self.line]

        if transfer_rendering:
            transfer_lines = list(self.get_transfer_lines())
            lines.extend(transfer_lines)
            lines.sort(key=lambda l: l.map_data.lines.index(l))

        logos_image = None

        for i, transfer_line in enumerate(lines):
            line_logo = transfer_line.logo_image
            line_logo.resize(round(
                line_logo.width
                / (line_logo.height / 48)
            ), 48)

            spacing = 16
            if i > 0 and lines[i - 1].type == "mcd" and transfer_line.type == "mcd":
                spacing = -10

            if i > 0:
                temp_image = Image(width=logos_image.width + spacing + line_logo.width, height=logos_image.height)
                place(temp_image, logos_image, (0, 0), RelativeTo.TOP_LEFT)
                place(temp_image, line_logo, (temp_image.width - 1, temp_image.height // 2), RelativeTo.RIGHT)
                logos_image = temp_image
            else:
                logos_image = line_logo

        place(sign_image, logos_image, (32, sign_image.height // 2), RelativeTo.LEFT)

        text_image = get_text_image(self.name, sign_image, self.line.map_data.font_path, font_size=30)
        place(sign_image, text_image, (48 + logos_image.width, sign_image.height // 2), RelativeTo.LEFT_DOWN)

        translit_name = transliterate.translit(self.name, 'ru', reversed=True)
        translit_text_image = get_text_image(translit_name, sign_image, self.line.map_data.font_path, font_color=Color("gray"), font_size=18)
        place(sign_image, translit_text_image, (46 + logos_image.width, sign_image.height // 2 + 6), RelativeTo.TOP_LEFT)

        round_corners(sign_image, 10 - frame_size)

        frame = Image(width=width, height=height, background=Color('#444450FF'), )

        place(frame, sign_image, (frame_size, frame_size), RelativeTo.TOP_LEFT)

        round_corners(frame, 10)

        return frame


class Line:
    @staticmethod
    def cmp(line1: "Line", line2: "Line"):
        return line1.priority - line2.priority

    def __init__(self, map_data, line_json):
        self.map_data = map_data
        self.name = line_json.get("name")

        if "line_filename" in line_json:
            self.line_image = Image(
                filename=os.path.join(
                    self.map_data.assets_path, "images", line_json.get("line_filename")
                )
            )
        else:
            self.line_image = Image(
                width=1, height=9, background=Color(line_json["line_color"])
            )

        if "planned_line_filename" in line_json:
            self.planned_line_image = Image(
                filename=os.path.join(
                    self.map_data.assets_path,
                    "images",
                    line_json.get("planned_line_filename"),
                )
            )
        elif "planned_line_color" in line_json:
            self.planned_line_image = Image(
                width=1, height=9, background=Color(line_json["planned_line_color"])
            )
        else:
            self.planned_line_image = None

        self.logo_image = Image(
            filename=os.path.join(
                self.map_data.assets_path, "images", line_json.get("logo_filename")
            )
        )

        self.logo_image_resized = Image(self.logo_image)
        self.logo_image_resized.resize(
            int(
                round(
                    self.logo_image_resized.width
                    / (self.logo_image_resized.height / (self.line_image.height * 3))
                )
                + 0.5
            ),
            self.line_image.height * 3,
        )

        self.type = line_json.get("type")
        self.priority = line_json.get("priority")
        self.bidirectional = line_json.get("bidirectional", False)

        self.start_logo_offset = tuple(line_json.get("start_logo_offset"))
        if self.start_logo_offset[0] is None or self.start_logo_offset[1] is None:
            self.start_logo_offset = None

        self.end_logo_offset = tuple(line_json.get("end_logo_offset"))
        if self.end_logo_offset[0] is None or self.end_logo_offset[1] is None:
            self.end_logo_offset = None

        self.start = line_json.get("start")
        self.direction = line_json.get("direction")

        self.elements: List[Element] = []
        cur_pos = self.start
        cur_direction = self.direction
        for element in line_json["elements"]:
            if element["type"] == "line_segment":
                self.elements.append(LineSegment(self, element))
                cur_pos = move(
                    cur_pos, element["length"], Direction[cur_direction.upper()]
                )
            if element["type"] == "turn":
                self.elements.append(Turn(self, element))
                cur_direction = element["direction"]
            if element["type"] == "station":
                self.elements.append(Station(self, element, cur_pos))

    def fix_stations_positions(self):
        cur_pos = self.start
        cur_direction = self.direction
        for element in self.elements:
            if isinstance(element, LineSegment):
                cur_pos = move(
                    cur_pos, element.length, Direction[cur_direction.upper()]
                )
            if isinstance(element, Turn):
                cur_direction = element.direction
            if isinstance(element, Station):
                element.position = cur_pos

    def get_station(self, station_name):
        for element in self.elements:
            if isinstance(element, Station) and element.name == station_name:
                return element
        return None

    @staticmethod
    def continue_line(coords, image, line_image, delta, direction):
        line_part = line_image.clone()
        line_part.resize(delta, line_part.height)
        if direction in ["up", "down"]:
            line_part.rotate(90)
        place(image, line_part, coords, RelativeTo[opposite(direction.upper())])
        return move(coords, delta, Direction[direction.upper()])

    @staticmethod
    def continue_with_first_station(
        metro_map_image, station, position, direction, station_image
    ):
        if not station.is_transfer():
            end_station = get_end_station(
                station_image, Orientation[opposite(direction.upper())]
            )
        else:
            end_station = get_transfer(
                station_image, station.line.type, Orientation[direction.upper()]
            )

        place(metro_map_image, end_station, position, RelativeTo.CENTER)

        if not station.is_transfer():
            position = move(
                position, station_image.height // 2 + 1, Direction[direction.upper()]
            )
        else:
            position = move(
                position, end_station.height // 2 + 1, Direction[direction.upper()]
            )

        return position

    @staticmethod
    def continue_with_station(
        metro_map_image, station, position, direction, line_image
    ):
        image_pos = tuple(position)

        if not station.is_transfer():
            station_image = get_station(
                line_image, Orientation[station.orientation.upper()]
            )
            image_pos = move(
                image_pos,
                line_image.height // 2 + (station.orientation in ["right", "down"]),
                Direction[station.orientation.upper()],
            )
        else:
            orientation = Orientation.HORIZONTAL
            if direction in ["up", "down"]:
                orientation = Orientation.VERTICAL
            station_image = get_transfer(line_image, station.line.type, orientation)

        place(
            metro_map_image,
            station_image,
            image_pos,
            RelativeTo[opposite(direction.upper())],
        )
        return move_by_image(position, station_image, direction)

    @staticmethod
    def continue_with_last_station(
        metro_map_image, station, position, direction, station_image
    ):
        if not station.is_transfer():
            end_station = get_end_station(station_image, Orientation[direction.upper()])
        else:
            end_station = get_transfer(
                station_image,
                station.line.type,
                Orientation[opposite(direction.upper())],
            )

        place(
            metro_map_image,
            end_station,
            position,
            RelativeTo[opposite(direction.upper())],
        )

    @staticmethod
    def continue_with_turn(metro_map_image, turn, position, direction, turn_image):
        arc = get_arc(
            turn_image, TurnType[direction.upper() + "_" + turn.direction.upper()]
        )
        image_pos = list(position)
        if direction == "right":
            if turn.direction == "down":
                image_pos[1] += -(turn_image.height // 2)
            else:
                image_pos[1] += (
                    -(turn_image.height // 2) - arc.height + turn_image.height
                )
        if direction == "down":
            if turn.direction == "left":
                image_pos[0] += (
                    -(turn_image.height // 2) + turn_image.height - arc.width
                )
            else:
                image_pos[0] += -(turn_image.height // 2)
        if direction == "left":
            image_pos[0] += -arc.width + 1
            if turn.direction == "up":
                image_pos[1] += (
                    -(turn_image.height // 2) - arc.height + turn_image.height
                )
            else:
                image_pos[1] += -(turn_image.height // 2)
        if direction == "up":
            image_pos[1] += -arc.width + 1
            if turn.direction == "right":
                image_pos[0] += -(turn_image.height // 2)
            else:
                image_pos[0] += (
                    -(turn_image.height // 2) + turn_image.height - arc.width
                )

        place(metro_map_image, arc, image_pos, RelativeTo.TOP_LEFT)

        position = move(
            position,
            arc.height - turn_image.height // 2 - 1,
            Direction[direction.upper()],
        )
        direction = turn.direction
        position = move(
            position, arc.height - turn_image.height // 2, Direction[direction.upper()]
        )

        return position, direction

    @staticmethod
    def draw_station_name(metro_map_image, station, font_path, highlight_color=None):
        if not station.hide_name:
            if highlight_color is None:
                text_image = get_text_image(station.name, metro_map_image, font_path)
            else:
                text_image = get_text_image(
                    station.name,
                    metro_map_image,
                    font_path,
                    Color("white"),
                    highlight_color,
                )

            place(
                metro_map_image,
                text_image,
                (
                    station.position[0] + station.name_offset[0],
                    station.position[1] + station.name_offset[1],
                ),
                RelativeTo[station.name_relative_to.upper()],
            )

    def draw_stations_names(self, metro_map_image, font_path, highlighted_station):
        for element in self.elements:
            if isinstance(element, Station):
                highlight_color = None
                if element == highlighted_station:
                    highlight_color = self.line_image[0, 0]
                Line.draw_station_name(
                    metro_map_image, element, font_path, highlight_color
                )

    def draw(self, metro_map_image):
        position = self.start
        direction = self.direction

        line_width = self.line_image.height
        station_length = get_station(self.line_image, Orientation.UP).width
        transfer_length = get_transfer(
            self.line_image, self.type, Orientation.RIGHT
        ).width
        turn_length = get_arc(self.line_image, TurnType.RIGHT_DOWN).width

        for num, element in enumerate(self.elements):
            element_image = (
                self.planned_line_image
                if element.is_actually_planned()
                else self.line_image
            )

            if isinstance(element, LineSegment):
                line_length = element.length

                if num != 0:
                    prev_element = self.elements[num - 1]
                    if isinstance(prev_element, Station):
                        line_length -= (
                            station_length // 2 + 1
                            if not prev_element.is_transfer()
                            else transfer_length // 2 + 1
                        )
                    elif isinstance(prev_element, Turn):
                        line_length -= turn_length - line_width // 2

                if num != len(self.elements) - 1:
                    next_element = self.elements[num + 1]
                    if isinstance(next_element, Station):
                        line_length -= (
                            station_length // 2
                            if not next_element.is_transfer()
                            else transfer_length // 2
                        )
                    elif isinstance(next_element, Turn):
                        line_length -= turn_length - line_width // 2 - 1

                if line_length < 0:
                    raise Exception("Line segment is too short")

                position = self.continue_line(
                    position, metro_map_image, element_image, line_length, direction
                )

            if isinstance(element, Station):
                if num == 0:
                    position = self.continue_with_first_station(
                        metro_map_image, element, position, direction, element_image
                    )
                elif num != len(self.elements) - 1:
                    position = self.continue_with_station(
                        metro_map_image, element, position, direction, element_image
                    )
                else:
                    self.continue_with_last_station(
                        metro_map_image, element, position, direction, element_image
                    )

            if isinstance(element, Turn):
                position, direction = self.continue_with_turn(
                    metro_map_image, element, position, direction, element_image
                )

    def draw_logos(self, metro_map_image):
        first_element = self.elements[0]
        if isinstance(first_element, Station):
            first_station_center = first_element.position
            if self.start_logo_offset is not None:
                place(
                    metro_map_image,
                    self.logo_image_resized,
                    [
                        first_station_center[0] + self.start_logo_offset[0],
                        first_station_center[1] + self.start_logo_offset[1],
                    ],
                    RelativeTo.CENTER,
                )

        last_element = self.elements[-1]
        if isinstance(last_element, Station):
            last_station_center = last_element.position
            if self.end_logo_offset[0] is not None:
                place(
                    metro_map_image,
                    self.logo_image_resized,
                    [
                        last_station_center[0] + self.end_logo_offset[0],
                        last_station_center[1] + self.end_logo_offset[1],
                    ],
                    RelativeTo.CENTER,
                )

    def get_linear_metro_map(self, reverse_direction, start_station_name=None):
        start_station = self.get_station(start_station_name)

        elements = list(self.elements)
        if reverse_direction:
            elements = list(reversed(elements))

        is_first_station = True
        if not self.bidirectional:
            if start_station_name is not None:
                for num, element in enumerate(elements):
                    if (
                        isinstance(element, Station)
                        and not element.is_actually_planned()
                    ):
                        if element == start_station:
                            elements = elements[num:]
                            break
                        is_first_station = False

        stations = [element for element in elements if isinstance(element, Station)]
        if not self.bidirectional:
            for num, station in enumerate(stations):
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
            if (
                station.is_transfer()
                or station == stations[len(stations) - 1]
                or station.name == start_station_name
            ):
                is_top = True

            name_length = get_text_image(
                station.name, temp_image, self.map_data.font_path
            ).width

            transfer_lines = station.get_transfer_lines()
            transfers_length = max(0, 10 * (len(transfer_lines) - 1))
            for line in transfer_lines:
                transfers_length += line.logo_image_resized.width
            stations_transfers_length.append(transfers_length)

            if is_top:
                station_position = max(
                    last_top + 40 + name_length // 2,
                    last_bottom + 40 + transfers_length // 2,
                )
                last_top = station_position + (name_length + 1) // 2
                last_bottom = station_position + (transfers_length + 1) // 2
            else:
                station_position = max(
                    last_top + 40, last_bottom + 40 + name_length // 2
                )
                last_top = station_position
                last_bottom = station_position + (name_length + 1) // 2

            if first_offset is None:
                first_offset = max(last_top, last_bottom) - 20

            stations_orientation.append("up" if is_top else "down")
            if prev_station_position is not None:
                line_segments_length.append(station_position - prev_station_position)

            prev_station_position = station_position
            is_top = not is_top

        total_width = max(last_top, last_bottom)

        direction_image = get_direction_image(
            self.logo_image_resized, stations[len(stations) - 1].name, self.map_data.font_path
        )
        reverse_direction_image = None
        if not (
            self.bidirectional
            and start_station_name == stations[len(stations) - 1].name
        ):
            total_width += direction_image.width
        else:
            total_width += 20
        if self.bidirectional and not start_station_name == stations[0].name:
            reverse_direction_image = get_direction_image(
                self.logo_image_resized, stations[0].name, self.map_data.font_path, True
            )
            total_width += reverse_direction_image.width

        linear_line = copy.copy(self)
        linear_line.elements = list(self.elements)
        linear_line.elements.clear()

        if not is_first_station:
            total_width += max(first_offset // 2, 50) - first_offset // 2
            linear_line.elements.append(
                LineSegment(linear_line, {"length": max(first_offset // 2 + 20, 50)})
            )

        linear_line.start_logo_offset = None
        linear_line.end_logo_offset = None
        linear_line.direction = "left"
        if is_first_station:
            linear_line.start = (total_width - 1 - 20 - first_offset // 2, 64)
        else:
            linear_line.start = (total_width - 1, 64)

        linear_metro_map_image = Image(
            width=total_width, height=128, background=Color("white")
        )
        linear_metro_map_image.virtual_pixel = "transparent"

        if not (
            self.bidirectional
            and start_station_name == stations[len(stations) - 1].name
        ):
            linear_metro_map_image.composite(direction_image)
        if self.bidirectional and not start_station_name == stations[0].name:
            linear_metro_map_image.composite(
                reverse_direction_image,
                left=linear_metro_map_image.width - reverse_direction_image.width,
            )
            linear_line.start = (
                linear_line.start[0] - reverse_direction_image.width,
                linear_line.start[1],
            )

        for num, station in enumerate(stations):
            if not station.is_transfer():
                station.orientation = stations_orientation[num]
                station.name_relative_to = opposite(station.orientation.upper()).lower()
            else:
                station.name_relative_to = "down"

            if station.orientation == "down":
                station.name_offset = (0, 20)
            else:
                station.name_offset = (0, -20)

            station.hide_name = False

            linear_line.elements.append(station)
            if num != len(stations) - 1:
                linear_line.elements.append(
                    LineSegment(linear_line, {"length": line_segments_length[num]})
                )

        linear_line.fix_stations_positions()

        for num, station in enumerate(stations):
            if station.is_transfer():
                cur_logo_pos = station.position[0] - stations_transfers_length[num] // 2
                for line in reversed(
                    sorted(station.get_transfer_lines(), key=cmp_to_key(Line.cmp))
                ):
                    transfer_logo = line.logo_image_resized
                    place(
                        linear_metro_map_image,
                        transfer_logo,
                        (cur_logo_pos, 100),
                        RelativeTo.LEFT,
                    )
                    cur_logo_pos += transfer_logo.width + 10

        linear_line.draw(linear_metro_map_image)
        linear_line.draw_stations_names(
            linear_metro_map_image, self.map_data.font_path, start_station
        )

        round_corners(linear_metro_map_image, 10)

        return complete_width(linear_metro_map_image)


class Transfer:
    def __init__(self, map_data, transfer_json):
        self.map_data = map_data
        self.stations = [
            map_data.get_station(
                (
                    transfer_json["station1"]["line_name"],
                    transfer_json["station1"]["station_name"],
                )
            ),
            map_data.get_station(
                (
                    transfer_json["station2"]["line_name"],
                    transfer_json["station2"]["station_name"],
                )
            ),
        ]
        self.is_direct = transfer_json["is_direct"]

    def draw(self, metro_map_image):
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

        line1 = self.stations[0].line
        line2 = self.stations[1].line
        color1 = line1.line_image[0, 0]
        color2 = line2.line_image[0, 0]
        mcd1 = line1.type == "mcd"
        mcd2 = line2.type == "mcd"

        coords1 = self.stations[0].position
        coords2 = self.stations[1].position
        mid = mult(add(coords1, coords2), 0.5)

        if self.is_direct:
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
                draw.stroke_color = Color("white")
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

            cur_coord = move_point(
                moved_coords1, moved_coords2, (dist - step * (count - 2)) / 2
            )

            for i in range(count - 1):
                with Drawing() as draw:
                    draw.stroke_color = Color("rgb(134, 164, 193)")
                    draw.fill_color = draw.stroke_color
                    draw.circle(cur_coord, add(cur_coord, (0.75, 0)))
                    draw(metro_map_image)
                    cur_coord = move_point(cur_coord, moved_coords2, step)


class MapData:
    def __init__(self, map_data_json: Dict[str, Any], assets_path):
        self.assets_path = assets_path
        self.image_resolution = tuple(map_data_json["image_resolution"])
        self.info_image = Image(
            filename=os.path.join(assets_path, "images", map_data_json["info_filename"])
        )
        self.font_path = os.path.join(
            assets_path, "fonts", map_data_json["font_filename"]
        )

        if "no_boarding_filename" in map_data_json:
            self.no_boarding_image = Image(
                filename=os.path.join(
                    assets_path, "images", map_data_json["no_boarding_filename"]
                )
            )
        else:
            self.no_boarding_image = None

        self.lines: List[Line] = []
        for line_json in map_data_json["lines"]:
            self.lines.append(Line(self, line_json))

        self.transfers: List[Transfer] = []
        if "transfers" in map_data_json:
            for transfer_json in map_data_json["transfers"]:
                cur_transfer = Transfer(self, transfer_json)
                self.transfers.append(cur_transfer)

                for station in cur_transfer.stations:
                    station.transfers.append(cur_transfer)

    def get_line(self, line_name: str):
        for line in self.lines:
            if line.name == line_name:
                return line
        return None

    def get_station(self, station_full_name: tuple[str, str]):
        line = self.get_line(station_full_name[0])
        return line.get_station(station_full_name[1]) if line is not None else None

    def get_max_text_length(self, metro_map_image):
        max_text_length = 0
        for line in self.lines:
            if line.name is not None:
                max_text_length = max(
                    max_text_length,
                    get_text_image(line.name, metro_map_image, self.font_path).width,
                )
        return max_text_length

    def draw_lines_info(self, metro_map_image):
        lines_image = Image(
            width=400 + self.get_max_text_length(metro_map_image),
            height=len(self.lines) * 33,
        )
        cur_top = 0
        for line in self.lines:
            place(lines_image, line.logo_image_resized, [30, cur_top + 20], RelativeTo.CENTER)

            line.line_image.resize(width=100)
            place(lines_image, line.line_image, [70, cur_top + 20], RelativeTo.LEFT)

            place(
                lines_image,
                get_text_image(line.name, metro_map_image, self.font_path),
                [190, cur_top + 20],
                RelativeTo.LEFT,
            )

            cur_top += 33

        metro_map_image.composite(
            lines_image, left=25, top=metro_map_image.height - lines_image.height - 20
        )

    def draw_info(self, metro_map_image):
        metro_map_image.composite(
            self.info_image,
            left=metro_map_image.width - self.info_image.width,
            top=metro_map_image.height - self.info_image.height,
        )

    def draw(self, highlighted_station=None):
        metro_map_image = Image(
            height=self.image_resolution[0],
            width=self.image_resolution[1],
            background=Color("white"),
        )
        for line in sorted(self.lines, key=cmp_to_key(Line.cmp)):
            line.draw(metro_map_image)
        for line in self.lines:
            line.draw_logos(metro_map_image)
        for transfer in self.transfers:
            transfer.draw(metro_map_image)
        for line in self.lines:
            line.draw_stations_names(
                metro_map_image, self.font_path, highlighted_station
            )
        self.draw_lines_info(metro_map_image)
        self.draw_info(metro_map_image)
        return metro_map_image
