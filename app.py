import requests
import logging

from flask import Flask, request, redirect, session, render_template

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/launch')
def launch():
    return render_template('launch.html')

@app.route('/patient')
def patient():
    return render_template('patient.html')

@app.route('/createpatient')
def createpatient():
    return render_template('createpatient.html')

@app.route('/listpatients')
def listpatients():
    return render_template('listpatients.html')

@app.route('/search')
def search():
    return render_template('search.html')

if __name__ == '__main__':
    import flaskbeaker

    flaskbeaker.FlaskBeaker.setup_app(app)

    logging.basicConfig(level=logging.DEBUG)
    #    make_ssl_devcert("cert.pem", host="localhost")
    #    app.run(debug=True, port=8000, ssl_context=('cert.pem', 'key.pem'))
    app.run(debug=True, port=5000)