import uuid
from fhirpy import SyncFHIRClient
import requests
import logging
import threading

from flask import Flask, request, redirect, session, render_template, url_for

app = Flask(__name__)

FHIR_SERVER_URL = "http://157.245.79.105:8080/fhir"

RESOURCE_TYPES = {
    "observation": "Observation",
    "careplan": "CarePlan",
    "medicationrequest": "MedicationRequest",
    "condition": "Condition",
    "goal": "Goal",
    "immunization": "Immunization"
}

client = SyncFHIRClient(FHIR_SERVER_URL)

def fetch_resources(resource_type, patient_id, result_container):
    resources = client.resources(resource_type).search(patient=patient_id).limit(100).fetch()
    result_container[resource_type] = resources

# View functions 

@app.route("/details/<patient_id>")
def view_patient_details(patient_id):
    resource_types = [
        "Observation", "CarePlan", "MedicationRequest",
        "Condition", "Goal", "Immunization"
    ]
    
    results = {}
    threads = []

    def fetch_resources(resource_type, patient_id, result_container):
        resources = client.resources(resource_type).search(patient=patient_id).limit(100).fetch()
        result_container[resource_type] = [r.to_dict() for r in resources]

    for r_type in resource_types:
        thread = threading.Thread(target=fetch_resources, args=(r_type, patient_id, results))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return render_template("patient_details.html", patient_id=patient_id, data=results)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/patient')
def patient():
    return render_template('patient.html')

@app.route("/createpatient", methods=["GET", "POST"])
def createpatient():
    if request.method == "POST":
        data = {
            "resourceType": "Patient",
            "name": [{"given": [request.form["given"]], "family": request.form["family"]}],
            "gender": request.form.get("gender"),
            "birthDate": request.form.get("birthDate")
        }
        client.resource("Patient", **data).save()
        return redirect(url_for("listpatients"))
    return render_template("patient_form.html", action="Create", patient=None)

@app.route("/editpatient/<patient_id>", methods=["GET", "POST"])
def editpatient(patient_id):
    patient = client.reference("Patient", patient_id).to_resource()
    
    if request.method == "POST":
        patient["name"][0]["given"] = [request.form["given"]]
        patient["name"][0]["family"] = request.form["family"]
        patient["gender"] = request.form.get("gender")
        patient["birthDate"] = request.form.get("birthDate")
        
        patient.save()
        
        return redirect(url_for("listpatients"))
    return render_template("patient_form.html", action="Edit", patient=patient)

@app.route("/deletepatient/<patient_id>", methods=["POST"])
def deletepatient(patient_id):
    client.reference("Patient", patient_id).to_resource().delete()
    return redirect(url_for("listpatients"))

@app.route('/listpatients', methods=["GET"])
def listpatients():
    search_query = client.resources("Patient")
    given = request.args.get("given")
    family = request.args.get("family")
    
    if given:
        search_query = search_query.search(given=given)
    if family:
        search_query = search_query.search(family=family)
    
    patients = search_query.limit(20).fetch()    
    return render_template('listpatients.html', patients=patients)

@app.route("/new/<patient_id>/<resource_type>", methods=["GET", "POST"])
def create_resource(patient_id, resource_type):
    if resource_type.lower() not in RESOURCE_TYPES:
        return "Unsupported resource type", 400

    resource_name = RESOURCE_TYPES[resource_type.lower()]
    
    if request.method == "POST":
        # Minimal sample; should validate fields
        data = {
            "resourceType": resource_name,
            "subject": {"reference": f"Patient/{patient_id}"}
        }
        # Add specific fields from form
        if resource_name == "Observation":
            data.update({
                "status": request.form["status"],
                "code": {"text": request.form["code"]},
                "valueString": request.form.get("value")
            })
        elif resource_name == "Goal":
            data.update({
                "description": {"text": request.form["description"]},
                "lifecycleStatus": request.form["status"]
            })
        elif resource_name == "Condition":
            data.update({
                "code": {"text": request.form["code"]},
                "clinicalStatus": {"text": request.form["status"]}
            })
        elif resource_name == "CarePlan":
            data.update({
                "status": request.form["status"],
                "intent": request.form["intent"],
                "title": request.form["title"]
            })
        elif resource_name == "MedicationRequest":
            data.update({
                "status": request.form["status"],
                "intent": request.form["intent"],
                "medicationCodeableConcept": {"text": request.form["medication"]}
            })
        elif resource_name == "Immunization":
            data.update({
                "status": request.form["status"],
                "vaccineCode": {"text": request.form["vaccine"]},
                "occurrenceDateTime": request.form["date"]
            })

        client.resource(resource_name, **data).save()
        return redirect(url_for("view_patient_details", patient_id=patient_id))

    return render_template("resource_form.html", patient_id=patient_id, resource_type=resource_type, action="Create")


@app.route("/edit/<patient_id>/<resource_type>/<resource_id>", methods=["GET", "POST"])
def edit_resource(patient_id, resource_type, resource_id):
    if resource_type.lower() not in RESOURCE_TYPES:
        return "Unsupported resource type", 400

    resource_name = RESOURCE_TYPES[resource_type.lower()]
    resource = client.reference(resource_name, resource_id).to_resource()

    if request.method == "POST":
        # Same structure as above
        if resource_name == "Observation":
            resource["status"] = request.form["status"]
            resource["code"] = {"text": request.form["code"]}
            resource["valueString"] = request.form.get("value")
        elif resource_name == "Goal":
            resource["description"] = {"text": request.form["description"]}
            resource["lifecycleStatus"] = request.form["status"]
        elif resource_name == "Condition":
            resource["code"] = {"text": request.form["code"]}
            resource["clinicalStatus"] = {"text": request.form["status"]}
        elif resource_name == "CarePlan":
            resource["status"] = request.form["status"]
            resource["intent"] = request.form["intent"]
            resource["title"] = request.form["title"]
        elif resource_name == "MedicationRequest":
            resource["status"] = request.form["status"]
            resource["intent"] = request.form["intent"]
            resource["medicationCodeableConcept"] = {"text": request.form["medication"]}
        elif resource_name == "Immunization":
            resource["status"] = request.form["status"]
            resource["vaccineCode"] = {"text": request.form["vaccine"]}
            resource["occurrenceDateTime"] = request.form["date"]
        
        resource.save()
        return redirect(url_for("details", patient_id=patient_id))

    return render_template("resource_form.html", patient_id=patient_id, resource_type=resource_type, action="Edit", resource=resource)


# Epic Oauth Connectivity

# SMART config
FHIR_AUTH_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
FHIR_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
FHIR_API_URL = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/"
CLIENT_ID = "ffb905d2-f94d-4cb5-a29c-0b048275f662"
REDIRECT_URI = "http://localhost:5000/Home"
SCOPES = "patient/launch,patient/Goal.write,patient/Goal.read,patient/Goal.search,patient/Observation.search,patient/Observation.read,patient/Observation.write,patient/Patient.read"

FHIR_AUTH_URL2 = "https://keycloak.testphysicalactivity.com/realms/physical_activity/protocol/openid-connect/auth"
FHIR_TOKEN_URL2 = "https://keycloak.testphysicalactivity.com/realms/physical_activity/protocol/openid-connect/token"
FHIR_API_URL2 = "https://fhir.testphysicalactivity.com/fhir/"
CLIENT_ID2 = "physical_activity"
REDIRECT_URI2 = "http://localhost:5000/call-back"
SCOPES2 = "patient/Patient.read"


@app.route("/launch")
def launch():
    state = str(uuid.uuid4())
    session["state"] = state
    launch = request.args.get("launch")  # optional Epic launch ID

    auth_url = (
        f"{FHIR_AUTH_URL}?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state={state}"
    )

    if launch:
        auth_url += f"&launch={launch}"

    print(auth_url)
    return redirect(auth_url)

@app.route("/Home")
def Home():
    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("state"):
        return "Error: Invalid state", 400

    # Token exchange
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID
    }

    response = requests.post(FHIR_TOKEN_URL, data=payload, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })

    if response.status_code != 200:
        return f"Error fetching token: {response.text}", 400

    token_data = response.json()
    session["access_token"] = token_data["access_token"]
    session["patient"] = token_data.get("patient")  # may be None for provider apps

    return redirect(url_for("epic"))

@app.route("/epic")
def epic():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("launch"))

    # Example: fetch Patient resource
    patient_id = session.get("patient")
    if not patient_id:
        return "No patient context provided", 400

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json"
    }

    patient = requests.get(f"{FHIR_API_URL}Patient/{patient_id}", headers=headers).json()

    return render_template("patient.html", patient=patient)

#Secure server

@app.route("/launch2")
def launch2():
    state = str(uuid.uuid4())
    session["state"] = state
    launch = request.args.get("launch")  # optional Epic launch ID

    auth_url = (
        f"{FHIR_AUTH_URL2}?response_type=code"
        f"&client_id={CLIENT_ID2}"
        f"&redirect_uri={REDIRECT_URI2}"
        f"&scope={SCOPES2}"
        f"&state={state}"
    )

    if launch:
        auth_url += f"&launch={launch}"
    
    return redirect(auth_url)

@app.route("/call-back")
def callBack():
    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("state"):
        return "Error: Invalid state", 400

    # Token exchange
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI2,
        "client_id": CLIENT_ID2
    }

    response = requests.post(FHIR_TOKEN_URL2, data=payload, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })

    if response.status_code != 200:
        return f"Error fetching token: {response.text}", 400

    token_data = response.json()
    print(token_data)
    session["access_token"] = token_data["access_token"]
    session["patient"] = token_data.get("patient")  # may be None for provider apps

    return redirect(url_for("secure"))

@app.route("/secure")
def secure():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("launch2"))    

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json"
    }

    patient = requests.get(f"{FHIR_API_URL2}Patient/", headers=headers).json()
    print(patient)

    return render_template("patient.html", patient=patient)
@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))  # or use "index" or "home" depending on your flow


if __name__ == '__main__':
    import flaskbeaker

    flaskbeaker.FlaskBeaker.setup_app(app)

    logging.basicConfig(level=logging.DEBUG)
    #    make_ssl_devcert("cert.pem", host="localhost")
    #    app.run(debug=True, port=8000, ssl_context=('cert.pem', 'key.pem'))
    app.run(debug=True, port=5000)