import os
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from tank_model.tank_core import io_helpers as ioh
from tank_model.tank_core import utils
from tank_model.tank_core import computation_helpers as ch
import json
import shutil
import pandas as pd
from tabulate import tabulate

import project_helper as ph
from project_config import UPLOADS, HOST_DB, PORT_DB, NAME_DB


def getRouteTank(app: Flask):
    # Database
    app.config["MONGO_URI"] = f"mongodb://{HOST_DB}:{PORT_DB}/{NAME_DB}"
    mongo = PyMongo(app)

    # Upload file excel with only 4 columns
    @app.route('/api/v1/data/upload', methods=['POST'])
    def upload():
        try:
            # validate file
            file = request.files['file_excel']
            if 'file_excel' not in request.files:
                raise Exception("No file part")
            elif file.filename == '':
                raise Exception("No selected file")
            elif not ph.allowed_file(file.filename):
                raise Exception("File is not allowed")

            # verify file input from client by column
            df = pd.read_excel(file)
            if len(df.columns) > 4:
                raise Exception("File only contain 4 columns")

            # check filename in use
            files = mongo.db.file.find_one(
                {'file': file.filename.split('.')[0].replace(' ', '').lower()})
            if files:
                raise Exception("File is exist")

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

    @app.route('/api/v1/data/getAll/categories', methods=['GET'])
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

    @app.route('/api/v1/data/<string:filename>/delete', methods=['DELETE'])
    def deleteModel(filename: str):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                raise FileNotFoundError("file is not exist")

            mongo.db.file.find_one_and_delete({'file': filename})
            shutil.rmtree(f'{UPLOADS}/{filename}')

            res = jsonify({'message': 'ok', 'filename': filename})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/data/tank/<string:filename>/getModel', methods=['GET'])
    def getModel(filename):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                raise FileNotFoundError("file is not exist")

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

            res = jsonify({'message': 'ok', 'basin': basin, 'stats': stats, 'precipitation': precipitation,
                           'discharge_td': discharge_td, 'discharge_tt': discharge_tt})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/data/tank/<string:filename>/optimize', methods=['PATCH'])
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
            statistics_pro = ph.read_stats_file(statistics_file)

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

            computation_result, _ = ch.compute_project(
                basin, precipitation, evapotranspiration, del_t)
            statistics = ch.compute_statistics(
                basin=basin, result=computation_result, discharge=discharge)

            statistics['BAHADURABAD']['R2'] = 0

            if statistics['BAHADURABAD']['NSE'] < 0.7:
                optimized_basin = ch.optimize_project(
                    basin, precipitation, evapotranspiration, discharge, del_t)

                with open(basin_file, 'w') as wf:
                    json.dump(optimized_basin, wf, indent=2)

                computation_result, _ = ch.compute_project(
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

            statistics_pro['BAHADURABAD'] = statistics['BAHADURABAD']

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics_pro, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok', 'result': list(
                computation_result['BAHADURABAD'])})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/data/tank/<string:filename>/compute', methods=['PATCH'])
    def computeModel(filename):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                res = jsonify({'message': 'file is not exist'})
                res.status_code = 404
                return res

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
            statistics_pro = ph.read_stats_file(statistics_file)

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

            computation_result, _ = ch.compute_project(
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

            statistics_pro['BAHADURABAD'] = statistics['BAHADURABAD']

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics_pro, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok', 'result': list(
                computation_result['BAHADURABAD'])})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v1/data/tank/<string:filename>/predict', methods=['POST'])
    def predictModel(filename):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                res = jsonify({'message': 'file is not exist'})
                res.status_code = 404
                return res

            if 'time' not in json.loads(request.data):
                raise Exception("Time is require!")

            if 'precipitation' not in json.loads(request.data):
                raise Exception("Precipitation is require!")

            if 'evapotranspiration' not in json.loads(request.data):
                raise Exception("Evapotranspiration is require!")

            time = json.loads(request.data)['time']
            prec = json.loads(request.data)['precipitation']
            et = json.loads(request.data)['evapotranspiration']

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")

            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            del_t_proj = project['interval']

            basin = ioh.read_basin_file(basin_file)
            precipitation, dt_pr = ph.read_ts_file(time, prec)
            evapotranspiration, dt_et = ph.read_ts_file(time, et)

            # check time difference consistancy
            del_t = utils.check_time_delta(dt_pr, dt_et, del_t_proj)

            computation_result, _ = ch.compute_project(
                basin, precipitation, evapotranspiration, del_t)

            computation_result['Time'] = pd.to_datetime(computation_result.index, utc=True)

            result = computation_result.to_dict(orient='records')

            res = jsonify({'message': 'ok', 'result': result})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
