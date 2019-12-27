from pymongo import MongoClient
import hashlib
import uuid
from urllib import unquote_plus
import datetime
import redis
import requests as r
import weficonfig
import sys

client = MongoClient(
    'mongodb://' + weficonfig.mongoip + ':27017/wefi')
print(client)
db = client['wefi']
reddisConnector = redis.StrictRedis(host=weficonfig.redisip, port=6379, db=0)


def getCityLocation(city):
    city = city.lower()
    latLng = reddisConnector.get(city)
    if not latLng:
        url = "http://www.mapquestapi.com/geocoding/v1/address?key=" + \
            weficonfig.mapquestapikey + "&location=" + str(city)
        try:
            latLng = r.get(url).json()['results'][0]['locations'][0]['latLng']
        except:
            print "Failed to fetch data from MapQuest"
            raise Exception()
        reddisConnector.set(
            city, str(latLng['lat']) + ":" + str(latLng['lng']))
        return latLng['lat'], latLng['lng']
    return latLng.split(":")[0], latLng.split(":")[1]


def findAPWithinRadious(lat, lng, radius):
    aps = db['wifiap']
    results = []
    query = aps.find({"location": {"$geoWithin": {"$centerSphere": [
        [float(lat), float(lng)], int(radius) / 3963.2]}}})
    for result in query:
        result.pop("_id", None)
        results.append(result)
    return results


def DuplicateAP(ssid, lat, lng):
    aps = db['wifiap']
    ssid = unquote_plus(ssid)
    query = aps.find({
        "ssid": str(ssid),
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)]
                },
                "$maxdistance": int(25)
            }
        }
    })
    if query.count() == 0:
        return False
    return True


def addAP(ssid, passwordenabled, password, lat, lng, username, sessionID):
    aps = db['wifiap']
    if not checkSession(username, sessionID):
        raise Exception()
    ssid = unquote_plus(ssid)
    password = unquote_plus(password)
    result = aps.insert({
        "location": {
            "coordinates": [float(lng), float(lat)],
            "type": "Point"
        },
        "ssid": str(ssid),
        "passwordenabled": passwordenabled,
        "password": password,
        "addedBy": username
    })


def doTheLogin(username, password):
    print('Searching for ' + username)
    users = db['users']
    query = users.find({
        "username": str(username)
    })
    print(query.count())
    sys.stdout.flush()
    if query.count() != 0:
        print('Found user')
        salt = query[0]['salt']
        hashed_password = hashlib.sha512(password + salt).hexdigest()
        if hashed_password == query[0]['password']:
            print('Passwords match')
            sessionID = addNewSession(username)
            return username, sessionID
    return None, None


def addNewSession(username):
    session = db['sessions']
    sessionID = hashlib.sha512(uuid.uuid4().hex).hexdigest()
    reddisConnector.set(sessionID, username)
    query = session.insert({
        "username": str(username),
        "session": str(sessionID),
    })
    return sessionID


def checkSession(username, sessionID):
    session = db['sessions']
    try:
        if reddisConnector.get(sessionID) == username:
            return True
    except:
        pass
    query = session.find({
        "username": str(username),
        "session": str(sessionID)
    })
    if query.count() == 0:
        return False
    try:
        reddisConnector.set(sessionID, username)
    except:
        pass
    return True


def deleteSession(username, sessionID):
    sessionDB = db['sessions']
    try:
        sessionsDB.delete_one({
            'username': username,
            'session': sessionID
        })
    except:
        pass
    reddisConnector.delete(sessionID)


def generateSalt():
    return uuid.uuid4().hex


def validateUserRegistration(username, password, email, recaptchachallenge, terms):
    if username == "":
        raise Exception()
    if password == "":
        raise Exception()
    if email == "":
        raise Exception()
    if recaptchachallenge == "":
        raise Exception()
    if not terms:
        raise Exception()
    GRA = r.post('https://www.google.com/recaptcha/api/siteverify',
                 data={
                     'secret': recaptchaKey,
                     'response': recaptchachallenge
                 }
                 ).json()
    if GRA['success'] == 'false':
        raise Exception()
    return True


def UserExists(username):
    users = db['users']
    query = users.find({
        "username": str(username)
    })
    if query.count == 0:
        return False
    return True


def apsCreatedBy(username):
    ap = db['wifiap']
    query = ap.find({
        'addedBy': username
    })
    return query
