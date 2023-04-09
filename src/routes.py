from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_pymongo import PyMongo
from tank_core import io_helpers as ioh
from tank_core import utils
from tank_core import computation_helpers as ch
import json
import pandas as pd
from tabulate import tabulate

import project_helper as ph
from config import UPLOADS


def getRoutes(app: Flask):
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

    # Upload file excel with only 4 columns
    @app.route('/api/v1/upload', methods=['POST'])
    def upload():
        try:
            # validate file
            file = request.files['file_excel']
            if 'file_excel' not in request.files:
                res = jsonify({'message': 'Bad request',
                              'content': 'No file part'})
                res.status_code = 400
                return res
            elif file.filename == '':
                res = jsonify({'message': 'Bad request',
                              'content': 'No selected file'})
                res.status_code = 400
                return res
            elif not ph.allowed_file(file.filename):
                res = jsonify({'message': 'Bad request',
                              'content': 'File is not allowed'})
                res.status_code = 400
                return res

            # verify file input from client
            df = pd.read_excel(file)
            if len(df.columns) > 4:
                res = jsonify({'message': 'Bad request',
                              'content': 'File only contain 4 columns'})
                res.status_code = 400
                return res

            # check filename in use
            files = mongo.db.file.find_one(
                {'file': file.filename.split('.')[0].replace(' ', '').lower()})
            if files:
                res = jsonify({'message': 'file is exist'})
                res.status_code = 403
                return res

            # create system file tank-model follow filename
            ph.create_file_project(file.filename.split('.')[0])
            ph.create_basin_file(file.filename.split('.')[0])
            ph.create_csv_file(df, file.filename.split('.')[0])
            ph.create_stats_file(file.filename.split('.')[0])

            # insert filename into database
            mongo.db.file.insert_one({
                'file': file.filename.split('.')[0].replace(' ', '').lower()
            })

            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/getAll', methods=['GET'])
    def getALl():
        try:
            filename = list(mongo.db.file.find({}, {'_id': 0}))

            res = jsonify({'message': 'ok', 'filename': filename})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/getModel/<string:filename>', methods=['GET'])
    def getModel(filename):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                res = jsonify({'message': 'file is not exist'})
                res.status_code = 404
                return res

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")
            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            stats_file = f"{UPLOADS}/{filename}/{project['statistics']}"
            discharge_file = f"{UPLOADS}/{filename}/{project['discharge']}"
            result_file = f"{UPLOADS}/{filename}/{project['result']}"
            precipitation_file = f"{UPLOADS}/{filename}/{project['precipitation']}"

            basin = ioh.read_basin_file(basin_file)
            stats = ph.read_stats_file(stats_file)
            _precipitation = pd.read_csv(precipitation_file)
            _discharge = pd.read_csv(discharge_file)
            _result = pd.read_csv(result_file)
            timeline = pd.read_csv(precipitation_file)['Time']

            # begin
            if 'begin' not in request.args:
                begin = str(_precipitation.Time[0]).split(' ')[0]
            else:
                begin = request.args['begin']

            # end
            if 'end' not in request.args:
                end = str(_precipitation.Time[len(
                    _precipitation.Time)-1]).split(' ')[0]
            else:
                end = request.args['end']

            head, tail = 0, 0
            if 'begin' in request.args or 'end' in request.args:
                for i in range(len(_precipitation.Time)):
                    if str(_precipitation.Time[i]).split(' ')[0] == begin:
                        head = i
                    if str(_precipitation.Time[i]).split(' ')[0] == end:
                        tail = i
                        break

                _precipitation = _precipitation.iloc[head:tail+1]
                _discharge = _discharge.iloc[head:tail+1]

            precipitation = ph.change_data_to_json_file(_precipitation)
            discharge_td = ph.change_data_to_json_file(_discharge)
            discharge_tt = ph.change_data_to_json_file(_result)

            res = jsonify({'message': 'ok', 'timeline': list(timeline), 'basin': basin, 'stats': stats, 'precipitation': precipitation,
                           'discharge_td': discharge_td, 'discharge_tt': discharge_tt})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/optimize/<string:filename>', methods=['PATCH'])
    def optimizeModel(filename):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                res = jsonify({'message': 'file is not exist'})
                res.status_code = 404
                return res

            if 'area' not in json.loads(request.data):
                raise Exception("area is required")

            area = json.loads(request.data)['area']

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")

            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            precipitation_file = f"{UPLOADS}/{filename}/{project['precipitation']}"
            evapotranspiration_file = f"{UPLOADS}/{filename}/{project['evapotranspiration']}"
            discharge_file = f"{UPLOADS}/{filename}/{project['discharge']}"
            statistics_file = f"{UPLOADS}/{filename}/{project['statistics']}"
            result_file = f"{UPLOADS}/{filename}/{project['result']}"

            basin = ioh.read_basin_file(basin_file)
            precipitation, dt_pr = ioh.read_ts_file(precipitation_file)
            evapotranspiration, dt_et = ioh.read_ts_file(
                evapotranspiration_file)
            discharge, _ = ioh.read_ts_file(
                discharge_file, check_time_diff=False)

            basin['basin_def']['BAHADURABAD']['area'] = area

            with open(basin_file, 'w') as basin_file_write_buffer:
                json.dump(basin, basin_file_write_buffer, indent=2)

            del_t_proj = project['interval']

            # begin
            if 'begin' not in json.loads(request.data):
                begin = str(precipitation.BAHADURABAD.index[0]).split(' ')[0]
            else:
                begin = json.loads(request.data)['begin']

            # end
            if 'end' not in json.loads(request.data):
                end = str(precipitation.BAHADURABAD.index[-1]).split(' ')[0]
            else:
                end = json.loads(request.data)['end']

            head, tail = 0, 0
            if 'begin' in json.loads(request.data) or 'end' in json.loads(request.data):
                for i in range(len(precipitation.BAHADURABAD)):
                    if str(precipitation.BAHADURABAD.index[i]).split(' ')[0] == begin:
                        head = i
                    if str(precipitation.BAHADURABAD.index[i]).split(' ')[0] == end:
                        tail = i
                        break

                precipitation = precipitation.iloc[head:tail+1]
                evapotranspiration = evapotranspiration.iloc[head:tail+1]
                discharge = discharge.iloc[head:tail+1]

            # check time difference consistancy
            del_t = utils.check_time_delta(dt_pr, dt_et, del_t_proj)

            computation_result = ch.compute_project(
                basin, precipitation, evapotranspiration, del_t)
            statistics = ch.compute_statistics(
                basin=basin, result=computation_result, discharge=discharge)

            statistics['BAHADURABAD']['R2'] = 0

            if statistics['BAHADURABAD']['NSE'] < 0.7:
                optimized_basin = ch.optimize_project(
                    basin, precipitation, evapotranspiration, discharge, del_t)

                with open(basin_file, 'w') as wf:
                    json.dump(optimized_basin, wf, indent=2)

                computation_result = ch.compute_project(
                    basin, precipitation, evapotranspiration, del_t)
                statistics = ch.compute_statistics(
                    basin=basin, result=computation_result, discharge=discharge)

            ioh.write_ts_file(computation_result, result_file)

            statistics['BAHADURABAD']['R2'] = 0

            print(
                tabulate(
                    [
                        ('NSE', statistics['BAHADURABAD']['NSE']),
                        ('RMSE', statistics['BAHADURABAD']['RMSE']),
                        ('R2', statistics['BAHADURABAD']['R2']),
                        ('PBIAS', statistics['BAHADURABAD']['PBIAS']),
                    ],
                    headers=['Statistics', 'BAHADURABAD'], tablefmt='psql'
                )
            )

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok', 'result': list(
                computation_result['BAHADURABAD'])})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/compute/<string:filename>', methods=['PATCH'])
    def computeModel(filename):
        try:
            if 'area' not in json.loads(request.data):
                raise Exception("area is required")

            if 'parameters' not in json.loads(request.data):
                raise Exception("parameters is required")

            area = json.loads(request.data)['area']
            parameter = json.loads(request.data)['parameters']

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")

            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            precipitation_file = f"{UPLOADS}/{filename}/{project['precipitation']}"
            evapotranspiration_file = f"{UPLOADS}/{filename}/{project['evapotranspiration']}"
            discharge_file = f"{UPLOADS}/{filename}/{project['discharge']}"
            statistics_file = f"{UPLOADS}/{filename}/{project['statistics']}"
            result_file = f"{UPLOADS}/{filename}/{project['result']}"

            basin = ioh.read_basin_file(basin_file)
            precipitation, dt_pr = ioh.read_ts_file(precipitation_file)
            evapotranspiration, dt_et = ioh.read_ts_file(
                evapotranspiration_file)
            discharge, _ = ioh.read_ts_file(
                discharge_file, check_time_diff=False)

            basin['basin_def']['BAHADURABAD']['area'] = area
            basin['basin_def']['BAHADURABAD']['parameters'] = parameter

            with open(basin_file, 'w') as basin_file_write_buffer:
                json.dump(basin, basin_file_write_buffer, indent=2)

            del_t_proj = project['interval']

            # begin
            if 'begin' not in json.loads(request.data):
                begin = str(precipitation.BAHADURABAD.index[0]).split(' ')[0]
            else:
                begin = json.loads(request.data)['begin']

            # end
            if 'end' not in json.loads(request.data):
                end = str(precipitation.BAHADURABAD.index[-1]).split(' ')[0]
            else:
                end = json.loads(request.data)['end']

            head, tail = 0, 0
            if 'begin' in json.loads(request.data) or 'end' in json.loads(request.data):
                for i in range(len(precipitation.BAHADURABAD)):
                    if str(precipitation.BAHADURABAD.index[i]).split(' ')[0] == begin:
                        head = i
                    if str(precipitation.BAHADURABAD.index[i]).split(' ')[0] == end:
                        tail = i
                        break

                precipitation = precipitation.iloc[head:tail+1]
                evapotranspiration = evapotranspiration.iloc[head:tail+1]
                discharge = discharge.iloc[head:tail+1]

            # check time difference consistancy
            del_t = utils.check_time_delta(dt_pr, dt_et, del_t_proj)

            computation_result = ch.compute_project(
                basin, precipitation, evapotranspiration, del_t)
            statistics = ch.compute_statistics(
                basin=basin, result=computation_result, discharge=discharge)

            ioh.write_ts_file(computation_result, result_file)

            statistics['BAHADURABAD']['R2'] = 0

            print(
                tabulate(
                    [
                        ('NSE', statistics['BAHADURABAD']['NSE']),
                        ('RMSE', statistics['BAHADURABAD']['RMSE']),
                        ('R2', statistics['BAHADURABAD']['R2']),
                        ('PBIAS', statistics['BAHADURABAD']['PBIAS']),
                    ],
                    headers=['Statistics', 'BAHADURABAD'], tablefmt='psql'
                )
            )

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok', 'result': list(
                computation_result['BAHADURABAD'])})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
