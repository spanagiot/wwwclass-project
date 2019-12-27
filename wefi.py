from flask import *
import weficonfig
from pymongo import MongoClient
from bson import json_util
import wefiapi
import hashlib
import requests as r
import sys
# Globals
app = Flask(__name__)
# Router


@app.route('/', methods=['GET', 'POST'])
def index():
    lat = 0
    lng = 0
    marker = False
    zoom = 0
    if request.method == 'POST':
        try:
            lat, lng = wefiapi.getCityLocation(request.form['city-search'])
            marker = True
            zoom = 14
        except:
            print "Failed to get city location"
    return Response(
        render_template(
            "index.html",
            lat=lat,
            lng=lng,
            marker=marker,
            zoom=zoom,
            title=weficonfig.WebpageTitle
        ),
        headers={
            "X-Xss-Protection": "1; mode=block",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
        }
    )


@app.route('/loginpage', methods=['GET', 'POST'])
def loginPage():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        loginResult = r.post(weficonfig.url + '/login', data={
            'username': username,
            'password': password
        }).json()
        print(loginResult)
        sys.stdout.flush()
        if loginResult['success'] == 'true':
            session['username'] = username
            session['sessionID'] = loginResult['sessionID']
            return redirect(url_for('index'))
    return Response(
        render_template(
            "login.html",
            title=weficonfig.WebpageTitle,
            errorMessage="",
            rc_site_key=weficonfig.rckey
        )
    )


@app.route('/registerpage', methods=['GET', 'POST'])
def registerPage():
    successMessage = ""
    errorMessage = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        recaptchachallenge = request.form['g-recaptcha-response']
        terms = "no"
        try:
            terms = request.form['terms']
        except:
            terms = "no"
        registerResult = r.post(weficonfig.url + '/register', data={
            'username': username,
            'password': password,
            'email': email,
            'recaptchachallenge': recaptchachallenge,
            'terms': terms
        })

        print(registerResult)
        registerResult = registerResult.json()
        if registerResult and registerResult['success'] == 'true':
            successMessage = "Register successfully"
        else:
            errorMessage = "Error during registration"
    return Response(
        render_template(
            "register.html",
            title=weficonfig.WebpageTitle,
            successMessage=successMessage,
            errorMessage=errorMessage,
            rc_site_key=weficonfig.rckey
        )
    )


@app.route('/addappage', methods=['GET', 'POST'])
def addAPPage():
    lat = 0
    lng = 0
    marker = False
    zoom = 0
    if request.method == 'POST':
        if (request.form['lat'] != '' and request.form['lng'] != '') and wefiapi.checkSession(session['username'], session['sessionID']):
            addAPResult = r.post(weficonfig.url + '/addap', data={
                'ssid': request.form['ssid'],
                'password': request.form['password'],
                'passwordenabled': True if request.form['password'] != "" else False,
                'sessionID': session['sessionID'],
                'lat': float(request.form['lat']),
                'lng': float(request.form['lng']),
                'username': session['username']
            }).json()
            print(addAPResult)
            sys.stdout.flush()
            return Response(
                render_template(
                    "addap.html",
                    lat=lat,
                    lng=lng,
                    marker=marker,
                    zoom=zoom,
                    title=weficonfig.WebpageTitle,
                    message=addAPResult['message'],
                    success=addAPResult['success']
                ),
                headers={
                    "X-Xss-Protection": "1; mode=block",
                    "X-Frame-Options": "SAMEORIGIN",
                    "X-Content-Type-Options": "nosniff",
                }
            )
    return Response(
        render_template(
            "addap.html",
            lat=lat,
            lng=lng,
            marker=marker,
            zoom=zoom,
            title=weficonfig.WebpageTitle,
            message='',
            success=True
        ),
        headers={
            "X-Xss-Protection": "1; mode=block",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
        }
    )


@app.route('/find/<lat>/<lng>/<radius>')
def returnAPs(lat, lng, radius):
    results = wefiapi.findAPWithinRadious(lat, lng, radius)
    return jsonify(results)


@app.route('/map')
def map():
    return Response(
        render_template(
            "map.html",
        ),
        headers={
            "X-Xss-Protection": "1; mode=block",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
        }
    )


@app.route('/addap', methods=['POST'])
def test():
    lat = float(request.form['lat'])
    lng = float(request.form['lng'])
    ssid = request.form['ssid']
    passwordenabled = request.form['passwordenabled']
    password = request.form['password']
    sessionID = request.form['sessionID']
    username = request.form['username']
    if not wefiapi.checkSession(username, sessionID):
        return Response('{"success":"false","session":"false"}', mimetype="text/json")
    APexists = False
    try:
        APexists = wefiapi.DuplicateAP(ssid, lat, lng)
    except Exception as e:
        print(e)
    if not APexists:
        try:
            wefiapi.addAP(ssid, passwordenabled, password,
                          lat, lng, username, sessionID)
        except:
            return Response('{"success":"false","message":"Error occured while adding AP"}', mimetype="text/json")
    else:
        return Response('{"success":"false","message":"AP already exists"}', mimetype="text/json")
    # print "Lat: " + str(lat) + " , Lng: " + str(lng) + " , SSID: " + str(ssid) + " , Password: " + str(password.encode("utf-8"))
    return Response('{"success":"true", "message":"AP added successfully"}', mimetype="text/json")


@app.route('/register', methods=['POST'])
def register():
    form = request.form.to_dict()
    print(form['username'])
    username = form['username']
    email = form['email']
    password = form['password']
    recaptchachallenge = form['recaptchachallenge']
    terms = form['terms']
    client = MongoClient('mongodb://' + weficonfig.mongoip + ':27017/wefi')
    print(username)
    db = client['wefi']
    users = db['users']
    salt = wefiapi.generateSalt()
    hashed_password = hashlib.sha512(password + salt).hexdigest()
    try:
        wefiapi.validateUserRegistration(
            username, password, email, recaptchachallenge, terms)
    except:
        return Response('{"success":"false","message":"Unknown error while adding user"}', mimetype="text/json")
    query = users.find({
        "username": str(username)
    })
    if query.count() == 0:
        result = users.insert({
            "username": str(username),
            "password": str(hashed_password),
            "salt": str(salt),
            "email": str(email)
        })
    else:
        return Response('{"success":"false","message":"Username already in use"}', mimetype="text/json")
    query = users.find({
        "username": str(username)
    })
    if query.count() == 0:
        return Response('{"success":"false","message":"Unknown error while adding user"}', mimetype="text/json")
    else:
        print query[0]
    return Response('{"success":"true","username":"' + str(query[0]['username']) + '", "id":"' + str(query[0]['_id']) + '" }', mimetype="text/json")


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    username, sessionID = wefiapi.doTheLogin(username, password)
    if username != None and sessionID != None:
        return Response('{"success":"true","username":"' + str(username) + '","sessionID":"' + str(sessionID) + '"}', mimetype="text/json")
    return Response('{"success":"false","message":"Username/Password Wrong"}', mimetype="text/json")


@app.route('/logout')
def logout():
    wefiapi.deleteSession(session['username'], session['sessionID'])
    session.clear()
    return redirect(url_for('index'))


@app.route('/profile/<string:username>')
def profile(username):
    if not wefiapi.UserExists(username):
        return redirect(url_for('index'))
    aps = []
    for ap in wefiapi.apsCreatedBy(username):
        aps.append(ap)
    return Response(
        render_template(
            "profile.html",
            profileUsername=username,
            apCreated=aps,
            numberApCreated=len(aps),
            title=weficonfig.WebpageTitle,
        )
    )


app.secret_key = weficonfig.SessionSecretKey

# Execution
if __name__ == '__main__':
    app.run(debug=False, threaded=True, host="0.0.0.0", port=80)
