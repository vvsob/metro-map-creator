from transliterate import translit

import datetime
import json
import os

from map_data import MapData, Station


def format_filename(filename):
    return translit(filename.replace(' ', '_').replace('\n', '_'), "ru", reversed=True)


start_time = datetime.datetime.now()

map_data = MapData(json.loads(open(os.path.join('input', 'map_data.json'), 'r').read()))

if not os.path.exists('output'):
    os.mkdir('output')
for file in os.listdir('output'):
    os.remove(os.path.join('output', file))

metro_map = map_data.draw()
metro_map.save(filename=os.path.join('output', 'metro_map.png'))

for line in map_data.lines:
    is_bidirectional = line.name in ['Первый диаметр', 'Второй диаметр', 'Филёвская']
    for element in line.elements:
        if isinstance(element, Station):
            for reverse_direction in [0, 1]:
                linear_metro_map = line.get_linear_metro_map(reverse_direction, element.name, is_bidirectional)

                linear_metro_map.save(filename=os.path.join('output', format_filename('linear_' + line.name + '_' +
                                                                                      element.name + '_' +
                                                                                      str(reverse_direction) + '.png')))

print(f'Generating completed in {int((datetime.datetime.now() - start_time).total_seconds() * 1000)} ms')
