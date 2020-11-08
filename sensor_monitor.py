"""
Starting of sensor data monitoring and analysis application -- 2020/10/01
"""
import json
import math
from flask import Flask, redirect, request
from jinja2 import Environment, PackageLoader, Markup, select_autoescape

app = Flask(__name__, static_url_path='/static')
env = Environment(
    loader=PackageLoader(__name__, 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

@app.route('/')
def root():
    template = env.get_template('main.html')
    return template.render()

@app.route('/m_monitor')
def monitor():
    template = env.get_template('m_monitor.html')
    return template.render()

@app.route('/m_dashboard')
def dashboard():
    template = env.get_template('m_dashboard.html')
    return template.render()

@app.route('/m_intro_1')
def intro_1():
    template = env.get_template('m_intro_1.html')
    return template.render()

@app.route('/m_intro_2')
def intro_2():
    template = env.get_template('m_intro_2.html')
    return template.render()

@app.route('/m_Ooops')
def Ooops():
    template = env.get_template('m_Ooops.html')
    return template.render()

@app.route('/post_monStart', methods=['POST'])
def post_monStart():
    data = json.loads(request.data)
    value = data['value']

    # Prepare data to send in here.
    val = ['xx.x','xx.xx','xx.x','xx.xx','xx.x','xx.xx','xx.xx','xxx.xxx','xxx.x','xxx.x','xxx.x']
    
    return json.dumps({ val })

@app.route('/post_graph', methods=['POST'])
def post_graph():
    data = json.loads(request.data)
    value = data['value']

    # Prepare data to send in here.
    x = []
    y = []
    for i in range(100):
        # Sine value for example.
        curr_x = float(i / 10)
        x.append(curr_x)
        y.append(math.sin(curr_x) * value)
    
    return json.dumps({ 'x': x, 'y': y })

if __name__ == '__main__':
    app.run(host='0.0.0.0')