import requests
import logging
from fhirpy import SyncFHIRClient
from fhirpy.base.exceptions import ResourceNotFound, MultipleResourcesFound
from flask import Flask, request, redirect, session, render_template, url_for

from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

from fhir.resources.humanname import HumanName
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.reference import Reference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.quantity import Quantity

import json


app = Flask(__name__)
serverurl = "http://157.245.79.105:8080/fhir"
client_id = "ffb905d2-f94d-4cb5-a29c-0b048275f662"
#83b5b8f4-6bca-4403-9e63-649d7b14b814
#http://hapi.fhir.org/baseR4
#https://server.fire.ly/R4

@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')


@app.route('/launch')
def launch():
    return render_template('launch.html')


@app.route('/Home')
def home():
    code = request.args.get("code")
    state = request.args.get("state")

    if code != "":
        # Define the OAuth2 client credentials and authorization code        
        redirect_uri = 'http://localhost:5000/Home'

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

        print(session['token'])

    return render_template('home.html', code=code, state=state, access_token=session['token'], patient=session['patient_id'])


@app.route('/Patient')
def patient():
    client = SyncFHIRClient(
        'https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/',
        authorization='Bearer ' + session['token'],
    )

    patients_resources = client.resources('Patient')

    try:
        patient = patients_resources.search(id=session['patient_id']).first()
        print(patient.serialize())
    except ResourceNotFound:
        pass
    except MultipleResourcesFound:
        pass

    # Search for patients
    return render_template('/patient.html', patient=patient)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        patientId = request.form['patientId']
        client = SyncFHIRClient(url=serverurl)
        patient = client.reference('Patient', patientId).to_resource()
        # Search for patients
        print(patient)
        return render_template('search.html', patient=patient, success=True)
    else:
        return render_template('search.html')


@app.route('/search1', methods=['GET', 'POST'])
def search1():
    if request.method == 'POST':
        name = request.form['name']
        client = SyncFHIRClient(url=serverurl)
        print(name)
        patients_resources = client.resources('Patient')

        patient0 = patients_resources.search(given=name).first();
        # Search for patients
        return render_template('search1.html', patient=patient0, success=True)
    else:
        return render_template('search1.html')


@app.route('/listpatients')
def listpatients():
    client = SyncFHIRClient(url=serverurl)
    resources = client.resources('Patient')
    resources = resources.search().limit(20)
    patients = resources.fetch()  # Returns list of FHIRResource

    print(patients)
    return render_template('/list.html', patientlist=patients)


@app.route('/getob')
def getob():
    client = SyncFHIRClient(url=serverurl)
    patientId = request.args.get("patientId")

    resources = client.resources('Observation')  # Return lazy search set
    resources = resources.search(patient=patientId).limit(10)
    observations = resources.fetch()  # Returns list of AsyncFHIRResource

    for ob in observations:
        print(ob)

    return render_template('/observations.html', observationlist=observations)


@app.route('/createob.html', methods=['GET', 'POST'])
def createob():
    if request.method == 'POST':
        patientId = request.form['patientId']
        client = SyncFHIRClient(url=serverurl)
        # here we are searching the patient by ID. Code for single read operation for a resource
        patient = client.reference('Patient', patientId).to_resource()
        print(patient.serialize())

        # this line tells the client which resource we are trying to fetch
        resources = client.resources('Observation')  # Return lazy search set
        #Searching based off patient ID and limiting the result set and then fetch brings the list of Observation FHIR resources
        observations = resources.search(patient=patientId).limit(10).fetch()

        for item in observations:
            print(item.serialize())
         # Returns list of FHIRResource

        return render_template('createob.html', success=True, observations=observations, patient=patient)

    return render_template('createob.html')


@app.route('/createObservation.html', methods=['GET', 'POST'])
def createObservation():
    patientId = request.args.get("patientId")
    client = SyncFHIRClient(url=serverurl)
    print(patientId)

    # Create Coding Object and attach it to observation
    coding = Coding()
    coding.system = "https://loinc.org"
    coding.code = "1920-8"
    coding.display = "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
    code = CodeableConcept()
    code.coding = [coding]

    observation = Observation(status="final", code=code)

    coding = Coding()
    coding.system = "https://terminology.hl7.org/CodeSystem/observation-category"
    coding.code = "laboratory"
    coding.display = "laboratory"
    category = CodeableConcept()
    category.coding = [coding]
    observation.category = [category]
    # Set our effective date time in our observation
    observation.effectiveDateTime = "2023-05-10T11:59:49+00:00"
    # Set our issued date time in our observation
    observation.issued = "2023-05-10T11:59:49.565+00:00"
    # Set our valueQuantity in our observation, valueQuantity which is made of a code, a unir, a system and a value
    valueQuantity = Quantity()
    valueQuantity.code = "U/L"
    valueQuantity.unit = "U/L"
    valueQuantity.system = "https://unitsofmeasure.org"
    valueQuantity.value = 50.395
    observation.valueQuantity = valueQuantity

    # Setting the reference to our patient using his id
    reference = Reference()
    reference.reference = f"Patient/{patientId}"
    observation.subject = reference

    print(observation.model_dump_json())
    client.resource('Observation', **json.loads(observation.model_dump_json())).save()

    print(observation)
    print("Observation created")

    return redirect(url_for('createob'))


@app.route('/edit.html')
def edit():
    client = SyncFHIRClient(url=serverurl)
    obId = request.args.get("ObservationId")
    ob_res = client.reference('Observation', obId).to_resource()
    # We are parsing the json and creating an object of observation
    observation = Observation.model_validate(ob_res.serialize())
    #we are updating the status of observation
    observation.status = "final"
    #now again we are converting the object in json and posting to the server
    client.resource('Observation', **json.loads(observation.model_dump_json())).save()


    return redirect(url_for('createob'))


@app.route('/delete.html')
def delete():
    client = SyncFHIRClient(url=serverurl)
    obId = request.args.get("ObservationId")
    print(obId)

    ob_ref = client.reference('Observation', obId)
    ob_res = ob_ref.to_resource()
    ob_res.delete()

    return redirect(url_for('createob'))


@app.route('/updatepatient.html')
def updatepatient():
    client = SyncFHIRClient(url=serverurl)
    patientId = request.args.get("PatientId")

    patient_ref = client.reference('Patient', patientId)
    patient_res = patient_ref.to_resource()

    patient = Patient.model_validate(patient_res.serialize())

    telecom = ContactPoint()

    telecom.value = '555-748-9999'
    telecom.system = 'phone'
    telecom.use = 'home'

    # Add our patient phone to it's dossier
    patient.telecom = [telecom]

    # Change the second given name of our patient to "anothergivenname"
    patient.name[0].given[1] = "anothergivenname"
    client.resource('Patient', **json.loads(patient.model_dump_json())).save()


    return redirect(url_for('index'))


if __name__ == '__main__':
    import flaskbeaker

    flaskbeaker.FlaskBeaker.setup_app(app)

    logging.basicConfig(level=logging.DEBUG)
    #    make_ssl_devcert("cert.pem", host="localhost")
    #    app.run(debug=True, port=8000, ssl_context=('cert.pem', 'key.pem'))
    app.run(debug=True, port=5000)