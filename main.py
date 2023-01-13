import json
import os

from metro_map_drawer import MetroMapDrawer


map_data = json.loads(open(os.path.join('input', 'map_data.json'), 'r').read())

metro_map_drawer = MetroMapDrawer(map_data)

metro_map = metro_map_drawer.get_metro_map()

if not os.path.exists('output'):
    os.mkdir('output')
metro_map.save(filename=os.path.join('output', 'metro_map.png'))
