from create_elements import *
from utilities import *
from functools import cmp_to_key


def cmp(line1, line2):
    return line1["priority"] - line2["priority"]


class MetroMapDrawer:
    def __init__(self, map_data):
        self._map_data = map_data

    def get_max_text_length(self, metro_map_image):
        max_text_length = 0
        for line in self._map_data["lines"]:
            if 'name' in line:
                max_text_length = max(max_text_length,
                                      get_text_image(line['name'], metro_map_image,
                                                     self._map_data['font_filename']).width)
        return max_text_length

    @staticmethod
    def get_line_img(line):
        line_img = None
        if 'filename' in line:
            line_img = Image(filename=os.path.join('images', line['filename']))
        elif 'color' in line:
            line_img = Image(width=1, height=9, background=Color(line['color']))
        return line_img

    @staticmethod
    def get_planned_img(line):
        planned_img = None
        if 'planned_filename' in line:
            planned_img = Image(filename=os.path.join('images', line['planned_filename']))
        elif 'planned_color' in line:
            planned_img = Image(width=1, height=9, background=Color(line['planned_color']))
        return planned_img

    @staticmethod
    def get_logo_img(line):
        line_img = MetroMapDrawer.get_line_img(line)
        logo_img = Image(filename=os.path.join('images', line['logo_filename']))
        logo_img.resize(line_img.height * 3, line_img.height * 3)
        return logo_img

    @staticmethod
    def continue_with_first_station(metro_map_image, element, position, direction, station_img, mcd):
        if element['type'] == 'station':
            end_station = get_end_station(station_img, Orientation[opposite(direction.upper())])
        else:
            end_station = get_transfer(station_img, mcd, Orientation[direction.upper()])

        station_center = place(metro_map_image, end_station, position, RelativeTo[opposite(direction.upper())])
        move_by_img(position, end_station, direction)

        return station_center

    @staticmethod
    def continue_with_station(metro_map_image, element, position, direction, station_img, mcd):
        img_pos = position.copy()

        if element['type'] == 'station':
            station = get_station(station_img, Orientation[element['orientation'].upper()])
            move(img_pos, station_img.height // 2 + (element['orientation'] in ['right', 'down']),
                 Direction[element['orientation'].upper()])
        else:
            orientation = Orientation.HORIZONTAL
            if direction in ['up', 'down']:
                orientation = Orientation.VERTICAL
            station = get_transfer(station_img, mcd, orientation)

        station_center = place(metro_map_image, station, img_pos, RelativeTo[opposite(direction.upper())])
        move_by_img(position, station, direction)

        if element['type'] == 'station':
            move(station_center, station_img.height // 2 + (element['orientation'] in ['right', 'down']),
                 Direction[opposite(element['orientation'].upper())])

        return station_center

    @staticmethod
    def continue_with_last_station(metro_map_image, element, position, direction, station_img, mcd):
        if element['type'] == 'station':
            end_station = get_end_station(station_img, Orientation[direction.upper()])
        else:
            end_station = get_transfer(station_img, mcd, Orientation[opposite(direction.upper())])

        station_center = place(metro_map_image, end_station, position, RelativeTo[opposite(direction.upper())])

        return station_center

    @staticmethod
    def draw_station_name(metro_map_image, element, station_center, font_filename):
        if element['name'] != '' and not ('hide_name' in element and element['hide_name']):
            text_img = get_text_image(element['name'], metro_map_image, font_filename)

            place(metro_map_image, text_img, [station_center[0] + element['name_offset'][0],
                                              station_center[1] + element['name_offset'][1]],
                  RelativeTo[element['name_relative_to'].upper()])

    @staticmethod
    def draw_line_stations_names(metro_map_image, line, stations_centers, font_filename):
        station_num = 0
        for element in line['elements']:
            if element['type'] in ['station', 'transfer']:
                MetroMapDrawer.draw_station_name(metro_map_image, element,
                                                 stations_centers[(line['name'], element['name'])], font_filename)
                station_num += 1

    @staticmethod
    def continue_with_turn(metro_map_image, element, position, direction, turn_img):
        arc = get_arc(turn_img, Turn[direction.upper() + '_' + element['direction'].upper()])
        img_pos = position.copy()
        if direction == 'right':
            if element['direction'] == 'down':
                img_pos[1] += -(turn_img.height // 2)
            else:
                img_pos[1] += -(turn_img.height // 2) - arc.height + turn_img.height
        if direction == 'down':
            if element['direction'] == 'left':
                img_pos[0] += -(turn_img.height // 2) + turn_img.height - arc.width
            else:
                img_pos[0] += -(turn_img.height // 2)
        if direction == 'left':
            img_pos[0] += -arc.width + 1
            if element['direction'] == 'up':
                img_pos[1] += -(turn_img.height // 2) - arc.height + turn_img.height
            else:
                img_pos[1] += -(turn_img.height // 2)
        if direction == 'up':
            img_pos[1] += -arc.width + 1
            if element['direction'] == 'right':
                img_pos[0] += -(turn_img.height // 2)
            else:
                img_pos[0] += -(turn_img.height // 2) + turn_img.height - arc.width

        place(metro_map_image, arc, img_pos, RelativeTo.TOP_LEFT)

        move(position, arc.height - turn_img.height // 2 - 1, Direction[direction.upper()])
        direction = element['direction']
        move(position, arc.height - turn_img.height // 2, Direction[direction.upper()])

        return direction

    @staticmethod
    def draw_line(line, metro_map_image):
        mcd = (line['type'] == 'mcd')

        line_img = MetroMapDrawer.get_line_img(line)
        planned_img = MetroMapDrawer.get_planned_img(line)

        logo_img = None
        if 'logo_filename' in line and 'name' in line:
            logo_img = Image(filename=os.path.join('images', line['logo_filename']))
            logo_img.resize(line_img.height * 3, line_img.height * 3)

        position = line['start']
        direction = line['direction']

        last_planned = False

        stations_centers = {}

        for (num, element) in enumerate(line['elements']):
            if element['type'] in ['station', 'transfer']:
                planned = False
                if 'planned' in element and element['planned']:
                    station_img = planned_img
                    planned = True
                else:
                    station_img = line_img

                if planned or last_planned:
                    prev_img = planned_img
                else:
                    prev_img = line_img

                last_planned = planned

                if num == 0:
                    cur_station_center = MetroMapDrawer.continue_with_first_station(metro_map_image, element,
                                                                                    position, direction, station_img,
                                                                                    mcd)
                elif num != len(line['elements']) - 1:
                    continue_line(position, metro_map_image, prev_img, element['offset'], direction)
                    cur_station_center = MetroMapDrawer.continue_with_station(metro_map_image, element,
                                                                              position, direction, station_img, mcd)
                else:
                    continue_line(position, metro_map_image, prev_img, element['offset'], direction)
                    cur_station_center = MetroMapDrawer.continue_with_last_station(metro_map_image, element,
                                                                                   position, direction, station_img,
                                                                                   mcd)
                stations_centers[(line['name'], element['name'])] = cur_station_center

            if element['type'] == 'turn':
                turn_img = line_img
                if last_planned:
                    turn_img = planned_img
                for element2 in line['elements'][num:]:
                    if element2['type'] in ['station', 'transfer']:
                        if 'planned' in element2 and element2['planned']:
                            turn_img = planned_img
                        break

                continue_line(position, metro_map_image, turn_img, element['offset'], direction)
                direction = MetroMapDrawer.continue_with_turn(metro_map_image, element, position, direction, turn_img)

        first_station_center = stations_centers[(line['name'], line['elements'][0]['name'])]
        if line['start_logo_offset'][0] is not None:
            place(metro_map_image, logo_img,
                  [first_station_center[0] + line['start_logo_offset'][0],
                   first_station_center[1] + line['start_logo_offset'][1]],
                  RelativeTo.CENTER)

        last_station_center = stations_centers[(line['name'], line['elements'][len(line['elements']) - 1]['name'])]
        if line['end_logo_offset'][0] is not None:
            place(metro_map_image, logo_img,
                  [last_station_center[0] + line['end_logo_offset'][0],
                   last_station_center[1] + line['end_logo_offset'][1]],
                  RelativeTo.CENTER)

        return stations_centers

    def draw_lines_info(self, metro_map_image):
        lines_img = Image(width=160 + self.get_max_text_length(metro_map_image),
                          height=len(self._map_data['lines']) * 40)
        cur_top = 0
        for line in self._map_data["lines"]:
            line_img = MetroMapDrawer.get_line_img(line)
            logo_img = MetroMapDrawer.get_logo_img(line)

            place(lines_img, logo_img, [0, cur_top + 20], RelativeTo.LEFT)

            line_img.resize(width=100)
            place(lines_img, line_img, [40, cur_top + 20], RelativeTo.LEFT)

            place(lines_img, get_text_image(line['name'], metro_map_image, self._map_data['font_filename']),
                  [160, cur_top + 20], RelativeTo.LEFT)

            cur_top += 40

        metro_map_image.composite(lines_img, left=25, top=metro_map_image.height - lines_img.height - 20)

    def draw_info(self, metro_map_image):
        info_img = Image(filename=os.path.join('images', self._map_data["info_filename"]))
        metro_map_image.composite(info_img, left=metro_map_image.width - info_img.width,
                                  top=metro_map_image.height - info_img.height)

    def draw_transfer(self, metro_map_image, transfer, stations_centers):
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

        color1 = None
        color2 = None
        mcd1 = False
        mcd2 = False
        for line in self._map_data['lines']:
            if line['name'] == transfer['station1']['line_name']:
                color1 = MetroMapDrawer.get_line_img(line)[0, 0]
                mcd1 = line['type'] == "mcd"
            if line['name'] == transfer['station2']['line_name']:
                color2 = MetroMapDrawer.get_line_img(line)[0, 0]
                mcd2 = line['type'] == "mcd"

        coords1 = tuple(stations_centers[(transfer["station1"]["line_name"], transfer["station1"]["station_name"])])
        coords2 = tuple(stations_centers[(transfer["station2"]["line_name"], transfer["station2"]["station_name"])])
        mid = mult(add(coords1, coords2), 0.5)

        if transfer['direct']:
            moved_coords1 = move_point(coords1, mid, 10)
            moved_coords2 = move_point(coords2, mid, 10)

            with Drawing() as draw:
                draw.stroke_color = color1
                draw.stroke_width = 9
                draw.line(moved_coords1, mid)
                draw(metro_map_image)

                draw.stroke_color = color2
                draw.stroke_width = 9
                draw.line(moved_coords2, mid)
                draw(metro_map_image)

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

            delta = dist / count

            cur_coord = move_point(moved_coords1, moved_coords2, (dist - delta * (count - 2)) / 2)

            for i in range(count - 1):
                with Drawing() as draw:
                    draw.stroke_color = Color("rgb(134, 164, 193)")
                    draw.fill_color = draw.stroke_color
                    draw.circle(cur_coord, add(cur_coord, (0.75, 0)))
                    draw(metro_map_image)
                    cur_coord = move_point(cur_coord, moved_coords2, delta)

    def get_metro_map(self):
        metro_map_image = Image(height=self._map_data["image_resolution"][0],
                                width=self._map_data["image_resolution"][1], background=Color('white'))

        stations_centers = {}
        for line in sorted(self._map_data["lines"], key=cmp_to_key(cmp)):
            stations_centers.update(self.draw_line(line, metro_map_image))

        for line in self._map_data["lines"]:
            self.draw_line_stations_names(metro_map_image, line, stations_centers, self._map_data['font_filename'])

        for transfer in self._map_data["transfers"]:
            self.draw_transfer(metro_map_image, transfer, stations_centers)

        self.draw_lines_info(metro_map_image)

        self.draw_info(metro_map_image)

        return metro_map_image
