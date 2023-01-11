import json
import os

from metro_map_drawer import MetroMapDrawer


map_data = json.loads(open('input.json', 'r').read())

metro_map_drawer = MetroMapDrawer(map_data)

metro_map = metro_map_drawer.get_metro_map()

if not os.path.exists('output'):
    os.mkdir('output')
metro_map.save(filename=os.path.join('output', 'res.png'))
