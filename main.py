from flask import Flask, render_template, url_for, jsonify, request
import serial
from struct import pack

import geo

s = None
try:
    s = serial.Serial('/dev/ttyACM0', 115200, timeout=0)
except:
    print "**** No serial ****"

ESCAPE = '\x13'
START = '\x37'

COMMAND_HELLO = '\x01'
COMMAND_LEDS = '\x02'
COMMAND_CLEAR = '\x03'
COMMAND_RENDER = '\x04'
COMMAND_TRANSITION = '\x05'

def send(data):
    if s:
        s.write(data)

def escape(data):
    return data.replace(ESCAPE, ESCAPE + ESCAPE)

def command_hello():
    ret = ESCAPE + START + COMMAND_HELLO
    return ret

def command_leds(leds):
    packed = [pack('BBB', rgb[1], rgb[0], rgb[2]) for rgb in leds]
    ret = ESCAPE + START + COMMAND_LEDS + chr(len(packed))
    for led in packed:
        ret += escape(led)
    return ret

def command_clear():
    ret = ESCAPE + START + COMMAND_CLEAR
    return ret

def command_render(mode):
    ret = ESCAPE + START + COMMAND_RENDER + pack('B', int(mode))
    return ret

def command_transition(mode):
    ret = ESCAPE + START + COMMAND_TRANSITION + pack('B', int(mode))
    return ret



import math
def hsv2rgb(h, s, v):
    h = float(h)
    s = float(s)
    v = float(v)
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = 0, 0, 0
    if hi == 0: r, g, b = v, t, p
    elif hi == 1: r, g, b = q, v, p
    elif hi == 2: r, g, b = p, v, t
    elif hi == 3: r, g, b = p, q, v
    elif hi == 4: r, g, b = t, p, v
    elif hi == 5: r, g, b = v, p, q
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return r, g, b


app = Flask(__name__)

@app.route('/rainbow/')
@app.route('/rainbow/<int:l>')
def rainbow(l=30):
    leds = [hsv2rgb((360.0 / float(l)) * float(i), 1, 0.5) for i in xrange(l)]
    send(command_leds(leds))
    return ''

@app.route('/color/<int:c>')
def color(c):
    send(command_transition(c))
    return ''

@app.route('/idle', methods=['GET','POST'])
def idle():
    send(command_transition(2))
    return ''

@app.route('/splash', methods=['GET','POST'])
def splash():
    send(command_transition(3))
    return ''

@app.route('/chooseSin', methods=['GET','POST'])
def choosesin():
    send(command_transition(9))
    return ''

@app.route('/sinDetail', methods=['GET','POST'])
def sindetail():
    send(command_transition(7))
    return ''

@app.route('/map', methods=['GET','POST'])
def map():
    send(command_transition(5))
    return ''

@app.route('/questionnaire', methods=['GET','POST'])
def questionnaire():
    send(command_transition(8))
    return ''

@app.route('/thankYou', methods=['GET','POST'])
def thankyou():
    send(command_transition(1))
    return ''

@app.route('/reportSin', methods=['POST'])
def reportsin():
    age = request.values.get('age', None)
    sex = request.values.get('sex', None)
    times_committed  = request.values.get('times_committed', None)
    commit_again = request.values.get('commit_again', None)
    sin = request.values.get('sin', None)
    sub_sin = request.values.get('sub_sin', None)
    lat = float(request.values.get('lat', None))
    long = float(request.values.get('long', None))

    neighborhood = geo.point_to_neighborhood(long, lat)

    print request.values

    """print '*********************************************************************************'
    print '** Sin Reported **'
    print 
    print 'Age: ', age
    print 'Sex:', sex
    print 'Times committed:', times_committed
    print 'Commit again?', commit_again
    print 'Sin category:', sin
    print 'Sin:', sub_sin"""
    print 'Neighborhood:', neighborhood

    return ''
    

@app.route('/test')
def test():
    print 'Inside test'
    return 'Test'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)