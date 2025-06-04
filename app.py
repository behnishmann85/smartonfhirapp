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


def getConnection(access_token):    
    if(access_token!=""):
        print('secured')
        client = SyncFHIRClient(
            FHIR_API_URL2,
            extra_headers={
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/fhir+json'
                }
            )
    else:
        client = SyncFHIRClient(FHIR_SERVER_URL)

    return client

def fetch_resources(resource_type, patient_id, result_container):
    access_token = session.get("access_token")
    resources = getConnection(access_token).resources(resource_type).search(patient=patient_id).limit(100).fetch()
    result_container[resource_type] = resources

# View functions
    
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
        access_token = session.get("access_token")
        getConnection(access_token).resource("Patient", **data).save()
        return redirect(url_for("listpatients"))
    return render_template("patient_form.html", action="Create", patient=None)

@app.route("/editpatient/<patient_id>", methods=["GET", "POST"])
def editpatient(patient_id):
    access_token = session.get("access_token")
    patient = getConnection(access_token).reference("Patient", patient_id).to_resource()
    
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
    access_token = session.get("access_token")
    getConnection(access_token).reference("Patient", patient_id).to_resource().delete()
    return redirect(url_for("listpatients"))

@app.route('/listpatients', methods=["GET"])
def listpatients():
    access_token = session.get("access_token")
    search_query = getConnection(access_token).resources("Patient")
    given = request.args.get("given")
    family = request.args.get("family")
    
    if given:
        search_query = search_query.search(given=given)
    if family:
        search_query = search_query.search(family=family)
    
    patients = search_query.limit(20).fetch()    
    return render_template('listpatients.html', patients=patients)

# ----------------- OBSERVATION ROUTES ------------------

@app.route('/observation/<patient_id>')
def list_observations(patient_id):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    observations = client.resources('Observation').search(patient=patient_id).limit(50).fetch()
    return render_template("observation_view.html", patient_id=patient_id,
                           observations=[o.serialize() for o in observations])

@app.route('/observationedit/<patient_id>', methods=["GET", "POST"])
@app.route('/observationedit/<patient_id>/<obs_id>', methods=["GET", "POST"])
def edit_observation(patient_id, obs_id=None):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    observation = None

    if obs_id:
        observation = client.resources('Observation').get(obs_id)
        obs_data = observation.serialize()
    else:
        obs_data = {}

    if request.method == "POST":
        form = request.form
        if observation:
            observation['valueQuantity']['value'] = float(form['value'])
            observation['valueQuantity']['unit'] = form['unit']
        else:
            observation = client.resource('Observation', {
                "status": "final",
                "code": {"text": form['code']},
                "subject": {"reference": f"Patient/{patient_id}"},
                "valueQuantity": {
                    "value": float(form['value']),
                    "unit": form['unit']
                }
            })
        observation.save()
        return redirect(url_for('list_observations', patient_id=patient_id))

    return render_template("observation_form.html", obs=obs_data, patient_id=patient_id)

@app.route('/goal/<patient_id>')
def list_goals(patient_id):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    goals = client.resources('Goal').search(patient=patient_id).limit(50).fetch()
    return render_template("goal_view.html", patient_id=patient_id,
                           goals=[g.serialize() for g in goals])


@app.route('/goaledit/<patient_id>', methods=["GET", "POST"])
@app.route('/goaledit/<patient_id>/<goal_id>', methods=["GET", "POST"])
def edit_goal(patient_id, goal_id=None):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    goal = None

    if goal_id:
        goal = client.resources('Goal').get(goal_id)
        goal_data = goal.serialize()
    else:
        goal_data = {}

    if request.method == "POST":
        form = request.form
        if goal:
            goal['description']['text'] = form['description']
            goal['lifecycleStatus'] = form['status']
        else:
            goal = client.resource('Goal', {
                "lifecycleStatus": form['status'],
                "description": {"text": form['description']},
                "subject": {"reference": f"Patient/{patient_id}"}
            })
        goal.save()
        return redirect(url_for('list_goals', patient_id=patient_id))

    return render_template("goal_form.html", goal=goal_data, patient_id=patient_id)


@app.route('/goaldelete/<patient_id>/<goal_id>', methods=["POST"])
def delete_goal(patient_id, goal_id):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    goal = client.resources('Goal').get(goal_id)
    goal.delete()
    return redirect(url_for('list_goals', patient_id=patient_id))

@app.route('/careplan/<patient_id>')
def list_careplans(patient_id):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    plans = client.resources('CarePlan').search(patient=patient_id).limit(50).fetch()
    return render_template("careplan_view.html", patient_id=patient_id,
                           careplans=[c.serialize() for c in plans])


@app.route('/careplanedit/<patient_id>', methods=["GET", "POST"])
@app.route('/careplanedit/<patient_id>/<careplan_id>', methods=["GET", "POST"])
def edit_careplan(patient_id, careplan_id=None):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    careplan = None

    if careplan_id:
        careplan = client.resources('CarePlan').get(careplan_id)
        plan_data = careplan.serialize()
    else:
        plan_data = {}

    if request.method == "POST":
        form = request.form
        if careplan:
            careplan['status'] = form['status']
            careplan['description'] = form['description']
            careplan['intent'] = form['intent']
            careplan['created'] = form['created']
        else:
            careplan = client.resource('CarePlan', {
                "status": form['status'],
                "intent": form['intent'],
                "description": form['description'],
                "created": form['created'],
                "subject": {"reference": f"Patient/{patient_id}"}
            })
        careplan.save()
        return redirect(url_for('list_careplans', patient_id=patient_id))

    return render_template("careplan_form.html", careplan=plan_data, patient_id=patient_id)


@app.route('/careplandelete/<patient_id>/<careplan_id>', methods=["POST"])
def delete_careplan(patient_id, careplan_id):
    access_token = session.get("access_token")
    client = getConnection(access_token)
    careplan = client.resources('CarePlan').get(careplan_id)
    careplan.delete()
    return redirect(url_for('list_careplans', patient_id=patient_id))

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

@app.route("/secure", methods=["GET", "POST"])
def secure():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("launch2"))   
     
    patients = getConnection(access_token).resources('Patient').fetch()
    return render_template('listpatients.html', patients=patients)

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