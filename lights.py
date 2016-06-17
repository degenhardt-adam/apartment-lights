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


# Load settings
with open('settings.json') as settings_file:
    settings = json.load(settings_file)


# Represents a set of bulbs in one physical place i.e. a "glass boob"
class Light:
    def __init__(self, bulbs):
        self.bulbs = bulbs

    def set(self, state):
        for bulb in self.bulbs:
            r = requests.put(
                settings['hue_url'] + '/lights/' + str(bulb) + '/state',
                json.dumps(state)
            )
            pprint(r.text)


# Represents a group of lights i.e. the bathroom
#
# Methods with the name *_handler handle incoming requests.
# For example, a request to /mainroom/on calls the mainroom LightGroup's
# on_handler() method.
#
# Methods with the name *_mode define continuous modes and have to be
# specially handled because of threading stuff. They should be started by calling
# start_mode(<mode>) and must end with the line 
# self.mode_ended = True
class LightGroup:
    def __init__(self, name, lights):
        self.lights = lights
        self.name = name
        self.on = False
        self.mode = 'none'
        self.mode_ended = False
        
        # Create group with Hue API
        group_bulbs = []
        for light in lights:
            for bulb in light.bulbs:
                group_bulbs.append(str(bulb))
        group_info = {
            'lights': group_bulbs,
            'name': name,
            'type': 'LightGroup'
        }
        try:
            r = requests.post(settings['hue_url'] + '/groups', json.dumps(group_info))
            self.group_id = json.loads(r.text)[0]['success']['id']
        except:
            pprint('Failed to create group ' + name)

        # Register group
        groups[name] = self


    # Handle /on
    def on_handler(self):
        self.on = True
        self.start_mode('on')

    # On mode
    def on_mode(self):
        while self.mode == 'on':
            self.set_group({
                'on': True,
                'bri': 254,
                'sat': settings['default_sat'],
                'hue': settings['default_color']
            })
            time.sleep(settings['on_delay'])
        self.mode_ended = True


    # Handle /off
    def off_handler(self):
        self.set_group({'on': False})
        self.on = False


    # Default handler. Toggle lights
    def default_handler(self):
        if self.on:
            self.off_handler()
        else:
            self.on_handler()


    # Handle /party
    def party_handler(self):
        self.start_mode('party')

    # Party mode
    def party_mode(self):
        self.set_group({
            'on': True,
            'bri': 254,
            'sat': 254
        })
        while self.mode == 'party':
            for light in self.lights:
                light.set({
                    'hue': rand.randint(0, 65535),
                    'transitiontime': settings['party_transition'],
                })
                time.sleep(settings['party_delay'] / len(self.lights))
                if self.mode != 'party':
                    break
        self.mode_ended = True



    # Helper method to set state of group
    def set_group(self, state):
        r = requests.put(
            settings['hue_url'] + '/groups/' + self.group_id + '/action',
            json.dumps(state)
        )
        pprint(r.text)


    # Begin mode
    def start_mode(self, mode):
        self.mode = mode
        method = getattr(self, mode + '_mode')
        thread.start_new_thread(method, ())

    # Used by the server to correctly switch between modes
    def end_mode(self):
        self.mode = 'none'
        while not self.mode_ended:
            pass
        self.mode_ended = False


# Initializing code beyond here. This runs once when the server is started.

# Clear groups
old_groups = requests.get(settings['hue_url'] + '/groups')
for group_id in old_groups.json().keys():
    pprint('Deleting group ' + group_id)
    requests.delete(settings['hue_url'] + '/groups/' + group_id)

# Registry of light groups
groups = {}

# Bulb numbers:
# 1 - Door A
# 2 - Door B
# 3 - Bedroom Lamp
# 4 - Bathroom Mirror Right
# 5 - Shower
# 6 - Desk A
# 7 - Bedroom Dresser
# 8 - Desk B
# 9 - Bathroom Mirror Left
# 10 - Kitchen
# 11 - Laundry A
# 12 - Laundry B
# 13 - Hallway A
# 14 - Hallway B
# 15 - Closet A
# 16 - Closet B

# Create groups
LightGroup('mainroom', [
    Light([1, 2]),
    Light([6, 8]),
    Light([10]),
    Light([11, 12]),
    Light([13, 14])
])
LightGroup('bedroom', [
    Light([3]),
    Light([7])
])
LightGroup('bathroom', [
    Light([4]),
    Light([5]),
    Light([9])
])
LightGroup('closet', [
    Light([15, 16])
])

pprint('Ready')



# Server code beyond here. Probably don't touch it.

# Called when server receives GET request to path
def handle_path(path):
    path_pieces = path.split('/')
    pprint(path_pieces)
    group = groups.get(path_pieces[1])
    if group:
        if group.mode != 'none':
            group.end_mode()
        try:
            method = getattr(group, path_pieces[2] + '_handler')
            method()
        except AttributeError:
            if not path_pieces[2]:
                group.default_handler()
            else:
                pprint('Invalid path: ' + path)
        except IndexError:
            group.default_handler()
    else:
        pprint('Invalid path: ' + path)

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header('Content-type', 'text/html')
        s.end_headers()

        pprint(s.path)
        try:
            handle_path(s.path)
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

