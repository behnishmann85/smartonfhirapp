import requests
import logging

from flask import Flask, request, redirect, session, render_template

app = Flask(__name__)


@app.route('/')
def home():
    return 'Hello, World!'


def launch():
    return render_template('launch.html')



@app.route('/Home2')
def home2():
    code = request.args.get("code")
    state = request.args.get("state")

    if code != "":
        # Define the OAuth2 client credentials and authorization code
        client_id = '83b5b8f4-6bca-4403-9e63-649d7b14b814'
        redirect_uri = 'https://localhost:5000/Home'

        # Define the token endpoint URL
        token_endpoint = 'https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token'

        # Define the request body parameters
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'code': code
        }

        # Send a POST request to the token endpoint to exchange the authorization code for an access token
        response = requests.post(token_endpoint, data=data)
        access_token = ''
        if response.status_code == 200:
            # Parse the response JSON and extract the access token and patient ID
            response_json = response.json()
            access_token = response_json.get('access_token')
            patient_id = response_json.get('patient')
            # Store the access token and patient ID in the session or elsewhere as appropriate
            session['token'] = access_token
            session['patient_id'] = patient_id
        else:
            # Handle the case where the request failed, e.g. by logging an error message or raising an exception
            print('Token request failed with status code', response.status_code)

    return render_template('home.html', code=code, state=state, access_token=session['token'], patient=session['patient_id'])


if __name__ == '__main__':
    import flaskbeaker

    flaskbeaker.FlaskBeaker.setup_app(app)

    logging.basicConfig(level=logging.DEBUG)
    #    make_ssl_devcert("cert.pem", host="localhost")
    #    app.run(debug=True, port=8000, ssl_context=('cert.pem', 'key.pem'))
    app.run(debug=True, port=5000)