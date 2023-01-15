from utilities import *


def get(dic, key, default=None):
    return dic[key] if key in dic else default


class Element:
    def __init__(self, line, is_planned):
        self.line = line
        self.is_planned = is_planned

    def is_actually_planned(self):
        num = self.line.elements.index(self)
        for element in self.line.elements[num:]:
            if element.is_planned is not None:
                if element.is_planned:
                    return True
                else:
                    break
            elif isinstance(element, Station):
                break

        for element in reversed(self.line.elements[:num + 1]):
            if element.is_planned is not None:
                if element.is_planned:
                    return True
                else:
                    break
            elif isinstance(element, Station):
                break

        return False


class LineSegment(Element):
    def __init__(self, line, line_segment_json, is_planned=None):
        super().__init__(line, is_planned)
        self.line = line
        self.length = get(line_segment_json, 'length')
        self.is_planned = get(line_segment_json, 'is_planned')


class Turn(Element):
    def __init__(self, line, turn_json, is_planned=None):
        super().__init__(line, is_planned)
        self.line = line
        self.direction = get(turn_json, 'direction')
        self.is_planned = get(turn_json, 'is_planned')


class Station(Element):
    def __init__(self, line, station_json, position, is_planned=None):
        super().__init__(line, is_planned)
        self.line = line
        self.name = get(station_json, 'name')
        self.name_offset = get(station_json, 'name_offset')
        self.orientation = get(station_json, 'orientation')
        self.name_relative_to = get(station_json, 'name_relative_to')
        self.hide_name = get(station_json, 'hide_name', False)
        self.is_planned = get(station_json, 'is_planned')

        self.position = position

        self.transfers = []

    def full_name(self):
        return self.line.name, self.name

    def is_transfer(self):
        return len(self.transfers) > 0


class Line:
    def __init__(self, map_data, line_json):
        self.map_data = map_data
        self.name = get(line_json, 'name')

        if 'line_filename' in line_json:
            self.line_image = Image(filename=os.path.join('input', 'images', get(line_json, 'line_filename')))
        else:
            self.line_image = Image(width=1, height=9, background=Color(line_json['line_color']))

        if 'planned_line_filename' in line_json:
            self.planned_line_image = Image(filename=os.path.join('input', 'images',
                                                                  get(line_json, 'planned_line_filename')))
        elif 'planned_line_color' in line_json:
            self.planned_line_image = Image(width=1, height=9, background=Color(line_json['planned_line_color']))
        else:
            self.planned_line_image = None

        self.logo_image = Image(filename=os.path.join('input', 'images', get(line_json, 'logo_filename')))
        self.logo_image.resize(int(round(self.logo_image.width /
                                         (self.logo_image.height / (self.line_image.height * 3))) + 0.5),
                               self.line_image.height * 3)

        self.type = get(line_json, 'type')
        self.priority = get(line_json, 'priority')

        self.start_logo_offset = tuple(get(line_json, 'start_logo_offset'))
        if self.start_logo_offset[0] is None or self.start_logo_offset[1] is None:
            self.start_logo_offset = None

        self.end_logo_offset = tuple(get(line_json, 'end_logo_offset'))
        if self.end_logo_offset[0] is None or self.end_logo_offset[1] is None:
            self.end_logo_offset = None

        self.start = get(line_json, 'start')
        self.direction = get(line_json, 'direction')

        self.elements = []

        cur_pos = self.start
        cur_direction = self.direction
        for element in line_json['elements']:
            if element['type'] == 'line_segment':
                self.elements.append(LineSegment(self, element))
                cur_pos = move(cur_pos, element['length'], Direction[cur_direction.upper()])
            if element['type'] == 'turn':
                self.elements.append(Turn(self, element))
                cur_direction = element['direction']
            if element['type'] == 'station':
                self.elements.append(Station(self, element, cur_pos))

    def get_station(self, station_name):
        for element in self.elements:
            if isinstance(element, Station) and element.name == station_name:
                return element
        return None


class Transfer:
    def __init__(self, map_data, transfer_json):
        self.map_data = map_data
        self.stations = [map_data.get_station((transfer_json['station1']['line_name'],
                                               transfer_json['station1']['station_name'])),
                         map_data.get_station((transfer_json['station2']['line_name'],
                                               transfer_json['station2']['station_name']))]
        self.is_direct = transfer_json['is_direct']


class MapData:
    def __init__(self, map_data_json):
        self.image_resolution = tuple(map_data_json['image_resolution'])
        self.info_image = Image(filename=os.path.join('input', 'images', map_data_json['info_filename']))
        self.font_filename = map_data_json['font_filename']

        self.lines = []
        for line_json in map_data_json['lines']:
            self.lines.append(Line(self, line_json))

        self.transfers = []
        if 'transfers' in map_data_json:
            for transfer_json in map_data_json['transfers']:
                cur_transfer = Transfer(self, transfer_json)
                self.transfers.append(cur_transfer)

                for station in cur_transfer.stations:
                    for another_station in cur_transfer.stations:
                        if station != another_station:
                            station.transfers.append(another_station)

    def get_line(self, line_name):
        for line in self.lines:
            if line.name == line_name:
                return line
        return None

    def get_station(self, station_full_name):
        line = self.get_line(station_full_name[0])
        return line.get_station(station_full_name[1]) if line is not None else None
