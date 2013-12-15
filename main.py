from flask import Flask, render_template, url_for, jsonify, request
import serial
from struct import pack
import json, os, datetime
import geo
import string
import random

#------------------------------------------------------------------------------
# try connecting to the arduino, fail gracefully

s = None
try:
    s = serial.Serial('/dev/ttyACM0', 115200, timeout=0)
except:
    print "**** No serial ****"

#------------------------------------------------------------------------------
# protocol with arduino

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

#------------------------------------------------------------------------------
# some helper functions

def parse_iso_datetime(str) :
    # parse a datetime generated by datetime.isoformat()
    try :
        return datetime.datetime.strptime(str, "%Y-%m-%dT%H:%M:%S")
    except ValueError :
        return datetime.datetime.strptime(str, "%Y-%m-%dT%H:%M:%S.%f")

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


#------------------------------------------------------------------------------
# some global state

SIN_FILENAME = 'sins.json'

categories = [
    'envy',
    'gluttony',
    'greed',
    'lust',
    'pride',
    'sloth',
    'wrath',
    'god',
    'violence',
    'society',
]

from collections import defaultdict
sins_per_neighborhood = defaultdict(int)
sins_per_category = defaultdict(int)
sins_per_sin = defaultdict(int)
sins_per_sex = defaultdict(int)
sins_per_category_per_neighborhood = {category : defaultdict(int) for category in categories}
total_sins = 0

sins_per_neighborhood.update({
    'Mission District' : 115,
    'South Beach' : 4,
    'Potrero Hill' : 37,
    'North Beach' : 96,
    'Mission Bay' : 13,
    'Inner Richmond' : 1,
    'Excelsior' : 107,
    'Bayview / Hunter\'s Point' : 3,
})

sins_per_category.update({
    'envy' : 45,
    'gluttony' : 54,
    'greed' : 45,
    'lust' : 67,
    'pride' : 34,
    'sloth' : 49,
    'wrath' : 78,
})

sins_per_sex.update({
    'female' : 104,
    'male' : 280,
})

category_colors = {
    'envy' : '#FF0000',
    'gluttony' : '#00FF00',
    'greed' : '#0000FF',
    'lust' : '#FFFF00',
    'pride' : '#00FFFF',
    'sloth' : '#FF00FF',
    'wrath' : '#ABABAB',
    'god' : '#2266FF',
    'violence' : '#FF0088',
    'society' : '#DD2243',
}

pivoted_data = {
    'gluttony': {
        'Bayview Park': 0,
        'Cole Valley': 4,
        'Excelsior': 14,
        'Financial District': 5,
        'Haight-Ashbury': 0,
        'Hayes Valley': 12,
        'Inner Richmond': 7,
        'Lower Haight': 5,
        'Lower Pacific Heights': 2,
        'Marina': 0,
        'Mission Bay': 3,
        'Mission District': 19,
        'Mission Dolores': 0,
        'Nob Hill': 0,
        'North Beach': 14,
        'Portrero Hill': 5,
        'The Castro/Upper Market': 9,
        'The Mission': 15,
        'Twin Peaks': 10,
        'Union Square': 0
    },
    'envy': {
        'Bayview Park': 0,
        'Cole Valley': 0,
        'Excelsior': 12,
        'Financial District': 1,
        'Haight-Ashbury': 0,
        'Hayes Valley': 10,
        'Inner Richmond': 4,
        'Lower Haight': 0,
        'Lower Pacific Heights': 0,
        'Marina': 0,
        'Mission Bay': 0,
        'Mission District': 12,
        'Mission Dolores': 5,
        'Nob Hill': 0,
        'North Beach': 12,
        'Portrero Hill': 3,
        'The Castro/Upper Market': 11,
        'The Mission': 11,
        'Twin Peaks': 6,
        'Union Square': 0
    },
    'greed': {
        'Bayview Park': 0,
        'Cole Valley': 0,
        'Excelsior': 6,
        'Financial District': 0,
        'Haight-Ashbury': 1,
        'Hayes Valley': 2,
        'Inner Richmond': 0,
        'Lower Haight': 0,
        'Lower Pacific Heights': 1,
        'Marina': 0,
        'Mission Bay': 0,
        'Mission District': 1,
        'Mission Dolores': 0,
        'Nob Hill': 0,
        'North Beach': 6,
        'Portrero Hill': 3,
        'The Castro/Upper Market': 1,
        'The Mission': 5,
        'Twin Peaks': 4,
        'Union Square': 0
    },
    'lust': {
        'Bayview Park': 1,
        'Cole Valley': 0,
        'Excelsior': 11,
        'Financial District': 0,
        'Haight-Ashbury': 0,
        'Hayes Valley': 16,
        'Inner Richmond': 0,
        'Lower Haight': 0,
        'Lower Pacific Heights': 0,
        'Marina': 0,
        'Mission Bay': 6,
        'Mission District': 47,
        'Mission Dolores': 0,
        'Nob Hill': 0,
        'North Beach': 12,
        'Portrero Hill': 6,
        'The Castro/Upper Market': 8,
        'The Mission': 20,
        'Twin Peaks': 8,
        'Union Square': 17
    },
    'pride': {
        'Bayview Park': 0,
        'Cole Valley': 0,
        'Excelsior': 26,
        'Financial District': 4,
        'Haight-Ashbury': 9,
        'Hayes Valley': 14,
        'Inner Richmond': 0,
        'Lower Haight': 0,
        'Lower Pacific Heights': 1,
        'Marina': 0,
        'Mission Bay': 0,
        'Mission District': 17,
        'Mission Dolores': 0,
        'Nob Hill': 4,
        'North Beach': 15,
        'Portrero Hill': 9,
        'The Castro/Upper Market': 12,
        'The Mission': 15,
        'Twin Peaks': 5,
        'Union Square': 0
    },
    'sloth': {
        'Bayview Park': 0,
        'Cole Valley': 0,
        'Excelsior': 20,
        'Financial District': 9,
        'Haight-Ashbury': 1,
        'Hayes Valley': 5,
        'Inner Richmond': 4,
        'Lower Haight': 3,
        'Lower Pacific Heights': 1,
        'Marina': 0,
        'Mission Bay': 7,
        'Mission District': 20,
        'Mission Dolores': 4,
        'Nob Hill': 7,
        'North Beach': 11,
        'Portrero Hill': 3,
        'The Castro/Upper Market': 14,
        'The Mission': 9,
        'Twin Peaks': 9,
        'Union Square': 0
    },
    'wrath': {
        'Bayview Park': 0,
        'Cole Valley': 0,
        'Excelsior': 19,
        'Financial District': 0,
        'Haight-Ashbury': 4,
        'Hayes Valley': 9,
        'Inner Richmond': 8,
        'Lower Haight': 0,
        'Lower Pacific Heights': 14,
        'Marina': 3,
        'Mission Bay': 0,
        'Mission District': 42,
        'Mission Dolores': 13,
        'Nob Hill': 3,
        'North Beach': 23,
        'Portrero Hill': 5,
        'The Castro/Upper Market': 0,
        'The Mission': 24,
        'Twin Peaks': 18,
        'Union Square': 0
    }
}

for category, data in pivoted_data.iteritems():
    sins_per_category_per_neighborhood[category].update(data)


def add_sin_to_global_data(sindata):

    global total_sins

    neighborhood = sindata.get('neighborhood')
    if neighborhood:
        sins_per_neighborhood[neighborhood] += 1

    sin_category = sindata.get('sin')
    if sin_category:
        sins_per_category[sin_category] += 1

    sin = sindata.get('sub_sin')
    if sin:
        sins_per_sin[sin] += 1

    sinner_sex = sindata.get('sex')
    if sinner_sex:
        sins_per_sex[sinner_sex] += 1

    if neighborhood and sin_category:
        sins_per_category_per_neighborhood[sin_category][neighborhood] += 1

    total_sins += 1

def load_global_data():
    if not os.path.exists(SIN_FILENAME):
        return

    with open(SIN_FILENAME) as sinsfile:
        for line in sinsfile:
            try:
                data = json.loads(line.strip())
                add_sin_to_global_data(data)
            except Exception, e:
                print 'Error parsing sin data:', e

def get_ticker_items():
    result = []

    total_in_neighborhoods = float(sum(sins_per_neighborhood.values()))
    for neighborhood, count in sins_per_neighborhood.iteritems():
        p = int(count / total_in_neighborhoods * 100)
        if p == 0: continue
        result.append('{}% of confessed sins were committed in {}'.format(p, neighborhood))

    total_in_categories = float(sum(sins_per_category.values()))
    for sin, count in sins_per_category.iteritems():
        p = int(count / total_in_categories * 100)
        if p == 0: continue
        result.append('{}% of sins are related to {}'.format(p, string.capwords(sin)))

    total_by_sex = float(sum(sins_per_sex.values()))
    for sex, count in sins_per_sex.iteritems():
        p = int(count / total_by_sex * 100)
        if p == 0: continue
        result.append('{}% of sins were committed by {}s'.format(p, sex))        

    max_neighborhood = max(sins_per_neighborhood.iterkeys(), key=(lambda k: sins_per_neighborhood[k]))
    max_category = max(sins_per_category.iterkeys(), key=(lambda k: sins_per_category[k]))
    max_sin = max(sins_per_sin.iterkeys(), key=(lambda k: sins_per_sin[k]))

    result.append('The neighborhood with the highest sin count is {}'.format(max_neighborhood))
    result.append('Most of the sins committed were related to {}'.format(string.capwords(max_category.encode('utf8'))))
    #result.append('The most confessed sin is {}'.format(string.capwords(max_sin.encode('utf8'))))

    random.shuffle(result)
    return result

#------------------------------------------------------------------------------
# flask app

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
    lat = float(request.values.get('lat', 0))
    long = float(request.values.get('long', 0))

    neighborhood = geo.point_to_neighborhood(long, lat)

    data = {
        'age' : age,
        'sex' : sex,
        'times_committed' : times_committed,
        'commit_again' : commit_again,
        'sin' : sin,
        'sub_sin' : sub_sin,
        'lat' : lat,
        'long' : long,
        'neighborhood' : neighborhood,
        'timestamp' : datetime.datetime.now().isoformat()
    }

    print '*********************************************************************************'
    print data

    add_sin_to_global_data(data)

    # note: not really json. each line is json but parsing the entire file as json will fail
    with open(SIN_FILENAME, 'a+b') as output:
        output.write(json.dumps(data) + os.linesep)
    
    return ''    

@app.route('/results')
def results():
    
    ndata = {}


    category, category_neighborhoods = random.choice(sins_per_category_per_neighborhood.items())
    category_color = category_colors[category]

    for neighborhood, count in category_neighborhoods.iteritems():
        ndata[neighborhood] = {
            "strokeColor": '#009ACD',
            "strokeOpacity": 0.9,
            "strokeWeight": 0.9,
            "fillColor": category_color, #'#4CB8DC',
            "fillOpacity": float(count) / float(sins_per_category[category])
        }

    ticker = get_ticker_items()

    context = {
        'data' : ndata,
        'ticker' : ticker,
        'category' : category.capitalize(),
        'category_color' : category_color,
    }

    return render_template('merge_style_hoods.html', **context)


@app.route('/test')
def test():
    print 'Inside test'
    return 'Test'

if __name__ == '__main__':
    load_global_data()
    app.run(host='0.0.0.0', port=5000, debug=True)