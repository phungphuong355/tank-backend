from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo
import json


def getRouteUser(app: Flask):
    # Database
    app.config["MONGO_URI"] = "mongodb://mongo:27017/duan"
    mongo = PyMongo(app)

    # Hello world
    @app.route('/', methods=['GET'])
    def hello():
        return "Welcome to Python Flask!"

    # Sign up a new user
    @app.route('/api/v1/signup', methods=['POST'])
    def signUp():
        try:
            # receipt request from user
            _json = json.loads(request.data)
            _fullName = _json['fullName']
            _phone = _json['phone']
            _email = _json['email']
            _password = _json['password']

            # file data from database
            user = mongo.db.users.find_one({'email': _email})
            if user:
                res = jsonify({'message': 'email in use'})
                res.status_code = 403
                return res

            # hash password
            hash_password = generate_password_hash(_password)

            # insert data into database
            createdUser = mongo.db.users.insert_one({
                'fullName': _fullName,
                'phone': _phone,
                'email': _email,
                'password': hash_password
            })

            res = jsonify({'message': 'User added successfully'})
            res.status_code = 201
            return res
        except Exception as error:

            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    # Sign in system
    @app.route('/api/v1/signin', methods=['POST'])
    def signIn():
        try:
            _json = json.loads(request.data)
            email = _json['email']
            password = _json['password']

            if email and password:
                user = mongo.db.users.find_one({'email': email})
                if user is None:
                    res = jsonify({'message': 'User not exists'})
                    res.status_code = 404
                    return res

                isMatch = check_password_hash(user['password'], password)
                if isMatch is False:
                    res = jsonify(
                        {'message': 'Email or password is not correct'})
                    res.status_code = 400
                    return res

            res = jsonify({'message': 'Login successfully'})
            res.status_code = 200
            return res
        except Exception as error:

            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/users', methods=['GET'])
    def getAllUser():
        try:
            users = list(mongo.db.users.find({}, {'_id': 0, 'password': 0}))

            res = jsonify({'message': 'ok', 'users': users})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/profile/<string:email>', methods=['GET'])
    def getProfile(email):
        try:
            user = mongo.db.users.find_one(
                {'email': email}, {'_id': 0, 'password': 0})
            if not user:
                raise Exception("user not found")

            res = jsonify({'message': 'ok', 'users': user})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/changePass/<string:email>', methods=['PATCH'])
    def changePassword(email: str):
        try:
            currentPass = json.loads(request.data)['currentPass']
            newPass = json.loads(request.data)['newPass']

            user = mongo.db.users.find_one({'email': email})
            if not user:
                raise Exception("user not found")

            isMatch = check_password_hash(user['password'], currentPass)
            if isMatch is False:
                raise Exception('Password is not correct')

            hashPass = generate_password_hash(newPass)

            mongo.db.users.update_one(
                {"email": email}, {"$set": {"password": hashPass}})

            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    # Sign out system
    @app.route('/api/v1/signout', methods=['POST'])
    def signOut():
        try:
            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
