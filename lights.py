"""
Server and http handlers for apartment light system
"""
import requests
import time
import thread
import json
import BaseHTTPServer
from pprint import pprint
import random as rand

"""
Define function names for handlers
path_to_handle, function name
"""

HANDLERS = {
    '/on': 'on',
    '/off': 'off',
    '/switch': 'switch',
    '/bed_on': 'bed_on',
    '/bed_off': 'bed_off',
    '/bed_switch': 'bed_switch',
    '/color': 'color',
    '/random': 'random',
    '/party': 'party'
}

# Load settings
with open('settings.json') as settings_file:
    settings = json.load(settings_file)

# Globals
global_state = {
    'default_color': True,
    'main_room_on': True,
    'bedroom_on': True,
    'party': False
}

# Toggle lights in main room
def switch():
    global_state['main_room_on'] = not global_state['main_room_on']
    global_state['party'] = False
    state = {
        'on': global_state['main_room_on']
    }
    set_group('1', state, global_state['default_color'])

# Turn on lights in main room
def on():
    global_state['main_room_on'] = True
    state = {
        'on': global_state['main_room_on']
    }
    set_group('1', state, global_state['default_color'])

# Turn off lights in main room
def off():
    global_state['main_room_on'] = False
    global_state['party'] = False
    state = {
        'on': global_state['main_room_on']
    }
    set_group('1', state, global_state['default_color'])

# Toggle lights in bedroom
def bed_switch():
    global_state['bedroom_on'] = not global_state['bedroom_on']
    state = {
        'on': global_state['bedroom_on']
    }
    set_group('2', state)

# Turn on lights in bedroom
def bed_on():
    global_state['bedroom_on'] = True
    state = {
        'on': global_state['bedroom_on']
    }
    set_group('2', state)

# Turn off lights in bedroom
def bed_off():
    global_state['bedroom_on'] = False
    state = {
        'on': global_state['bedroom_on']
    }
    set_group('2', state)

# Change color of lights in main room
def color():
    global_state['party'] = False
    global_state['default_color'] = not global_state['default_color']
    set_group('1', {}, global_state['default_color'])

# Set main room color to random color
def random():
    hue = rand.randint(0, 65535)
    set_group('1', {'hue': hue})

# Start party mode
def party():
    on()
    global_state['party'] = not global_state['party']
    if global_state['party']:
        thread.start_new_thread(party_mode, ())

# Party mode internals
def party_mode():
    group = 3
    groups = {
        3: ['1', '2'],
        4: ['6', '8'],
        5: ['10'],
        6: ['11', '12'],
        7: ['13', '14']
    }
    while global_state['party']:
        hue = rand.randint(0, 65535)
        for light in groups[group]:
            set_light(light, {'hue': hue, 'transitiontime': settings['party_transition']})
        group += 1
        if group > 7:
            group = 3
        time.sleep(settings['party_delay'])
    on()

# Helper function. Set state of a group
def set_group(group, state, default_color=True):
    if default_color:
        set_state = {
            'bri': 254,
            'sat': settings['default_sat'],
            'hue': settings['default_color']
        }
    else:
        set_state = {
            'bri': 254,
            'sat': settings['alt_sat'],
            'hue': settings['alt_color']
        }
    set_state.update(state)
    r = requests.put(settings['hue_url'] + '/groups/' + group + '/action', json.dumps(set_state))
    pprint(r.text)

# Helper function. Set state of a light
def set_light(light, state):
    r = requests.put(settings['hue_url'] + '/lights/' + light + '/state', json.dumps(state))
    pprint(r.text)



# Server code. Probably don't touch this
class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header('Content-type', 'text/html')
        s.end_headers()

        pprint(s.path)
        try:
            handler = HANDLERS[s.path]
            globals()[handler]()
        except KeyError:
            pass
    def do_GET(s):
        s.do_HEAD()

if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((settings['host_name'], 80), MyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()

