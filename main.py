from transliterate import translit

import json
import os

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
            for direction in [1, 0]:
                linear_metro_map = metro_map_drawer.get_linear_metro_map(direction, line['name'], element['name'])
                linear_metro_map.save(filename=os.path.join('output', format_filename('linear_' + line['name'] + '_' +
                                                                                      element['name'] + '_' +
                                                                                      str(direction) + '.png')))
