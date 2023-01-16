from transliterate import translit

import json
import os

from wand.color import Color
from wand.image import Image

from metro_map_drawer import MetroMapDrawer


def format_filename(filename):
    return translit(filename.replace(' ', '_').replace('\n', '_'), "ru", reversed=True)


map_data = json.loads(open(os.path.join('input', 'map_data.json'), 'r').read())

metro_map_drawer = MetroMapDrawer(map_data)

if not os.path.exists('output'):
    os.mkdir('output')

metro_map = metro_map_drawer.get_metro_map()
metro_map.save(filename=os.path.join('output', 'metro_map.png'))

for line in map_data['lines']:
    for element in line['elements']:
        if element['type'] == 'station':
            for reverse_direction in [0, 1]:
                linear_metro_map = metro_map_drawer.get_linear_metro_map(reverse_direction, line['name'],
                                                                         element['name'])

                map_width = linear_metro_map.width
                total_width = (map_width + 128 - 1) // 128 * 128
                if total_width // 128 % 2 == 0:
                    total_width += 128

                formatted_map = Image(width=total_width, height=128, background=Color('#FFFFFF00'))
                formatted_map.composite(linear_metro_map, left=(total_width - map_width) // 2)

                formatted_map.save(filename=os.path.join('output', format_filename('linear_' + line['name'] + '_' +
                                                                                   element['name'] + '_' +
                                                                                   str(reverse_direction) + '.png')))
