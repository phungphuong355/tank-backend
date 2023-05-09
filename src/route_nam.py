import json
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from tank_model.tank_core import io_helpers as ioh
from Nam import Nam

from project_config import HOST_DB, NAME_DB, PORT_DB, UPLOADS
import project_helper as ph


def getRouteNam(app: Flask):
    # Database
    app.config["MONGO_URI"] = f"mongodb://{HOST_DB}:{PORT_DB}/{NAME_DB}"
    mongo = PyMongo(app)

    @app.route('/api/v2/data/nam/<string:filename>/getModel', methods=['GET'])
    def getNamModel(filename: str):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                raise FileNotFoundError("file is not exist")

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")
            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            stats_file = f"{UPLOADS}/{filename}/{project['statistics']}"
            discharge_file = f"{UPLOADS}/{filename}/{project['discharge']}"
            result_file = f"{UPLOADS}/{filename}/{filename}.nam.csv"
            precipitation_file = f"{UPLOADS}/{filename}/{project['precipitation']}"

            basin = ioh.read_basin_file(basin_file)
            stats = ph.read_stats_file(stats_file)
            _precipitation = pd.read_csv(precipitation_file)
            _discharge = pd.read_csv(discharge_file)
            _result = pd.read_csv(result_file)

            _result = _result.drop(['Temp', 'P', 'E', 'Q', 'Lsoil'], axis=1)
            _result.columns = ['Time', 'BAHADURABAD']

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

    @app.route('/api/v2/data/nam/<string:filename>/compute', methods=['PATCH'])
    def computeNamModel(filename: str, cal=False):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                raise FileNotFoundError("file is not exist")

            # Validate
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

            basin = ioh.read_basin_file(basin_file)
            precipitation = pd.read_csv(precipitation_file)
            evapotranspiration = pd.read_csv(evapotranspiration_file)
            discharge = pd.read_csv(discharge_file)
            statistics = ph.read_stats_file(statistics_file)

            basin['basin_def']['BAHADURABAD']['area'] = area
            basin['basin_def']['BAHADURABAD']['nam'] = parameter
            basin['basin_def']['BAHADURABAD']['nam']['csnow'] = 0
            basin['basin_def']['BAHADURABAD']['nam']['snowtemp'] = 0

            with open(basin_file, 'w') as basin_file_write_buffer:
                json.dump(basin, basin_file_write_buffer, indent=2)

            del_t_proj = project['interval']

            # Merge dataset
            df_nam = discharge
            df_nam.columns = ['Date', 'Q']
            df_nam['P'] = precipitation['BAHADURABAD']
            df_nam['E'] = evapotranspiration['BAHADURABAD']
            df_nam.insert(1, 'Temp', [0]*len(df_nam['Date']))
            df_nam = df_nam.set_index('Date')

            # begin
            if 'begin' not in json.loads(request.data):
                begin = str(df_nam.index[0]).split(' ')[0]
            else:
                begin = json.loads(request.data)['begin']

            # end
            if 'end' not in json.loads(request.data):
                end = str(df_nam.index[-1]).split(' ')[0]
            else:
                end = json.loads(request.data)['end']

            head, tail = 0, 0
            if 'begin' in json.loads(request.data) or 'end' in json.loads(request.data):
                for i in range(len(df_nam.index)):
                    if str(df_nam.index[i]).split(' ')[0] == begin:
                        head = i
                        break
                for i in range(len(df_nam.index)):
                    if str(df_nam.index[i]).split(' ')[0] == end:
                        tail = i
                        break

                df_nam = df_nam.iloc[head:tail+1]

            # Initilize object
            nam = Nam(Filename=filename, Area=area, Cal=cal, DeltaT=del_t_proj)
            # Process path
            nam.process_path = rf'{UPLOADS}/{filename}'
            # Parameters
            nam.initial = np.array([parameter['umax'], parameter['lmax'], parameter['cqof'], parameter['ckif'],
                                    parameter['ck12'], parameter['tof'], parameter['tif'], parameter['tg'],
                                    parameter['ckbf'], 0, 0])
            # Dataset
            nam.df = df_nam

            # Run NAM
            nam.run()
            nam.stats()
            nam.update()

            statistics['NAM'] = dict(
                NSE=nam.NSE,
                RMSE=nam.RMSE
            )

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v2/data/nam/<string:filename>/optimize', methods=['PATCH'])
    def optimizeNamModel(filename: str, cal=True):
        try:
            files = mongo.db.file.find_one({'file': filename})
            if not files:
                raise FileNotFoundError("file is not exist")

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

            basin = ioh.read_basin_file(basin_file)
            precipitation = pd.read_csv(precipitation_file)
            evapotranspiration = pd.read_csv(evapotranspiration_file)
            discharge = pd.read_csv(discharge_file)
            statistics = ph.read_stats_file(statistics_file)

            basin['basin_def']['BAHADURABAD']['area'] = area

            with open(basin_file, 'w') as basin_file_write_buffer:
                json.dump(basin, basin_file_write_buffer, indent=2)

            del_t_proj = project['interval']

            # Merge dataset
            df_nam = discharge
            df_nam.columns = ['Date', 'Q']
            df_nam['P'] = precipitation['BAHADURABAD']
            df_nam['E'] = evapotranspiration['BAHADURABAD']
            df_nam.insert(1, 'Temp', [0]*len(df_nam['Date']))
            df_nam = df_nam.set_index('Date')

            # begin
            if 'begin' not in json.loads(request.data):
                begin = str(df_nam.index[0]).split(' ')[0]
            else:
                begin = json.loads(request.data)['begin']

            # end
            if 'end' not in json.loads(request.data):
                end = str(df_nam.index[-1]).split(' ')[0]
            else:
                end = json.loads(request.data)['end']

            head, tail = 0, 0
            if 'begin' in json.loads(request.data) or 'end' in json.loads(request.data):
                for i in range(len(df_nam.index)):
                    if str(df_nam.index[i]).split(' ')[0] == begin:
                        head = i
                        break
                for i in range(len(df_nam.index)):
                    if str(df_nam.index[i]).split(' ')[0] == end:
                        tail = i
                        break

                df_nam = df_nam.iloc[head:tail+1]

            # Initilize object
            nam = Nam(Filename=filename, Area=area, Cal=cal, DeltaT=del_t_proj)
            # Process path
            nam.process_path = rf'{UPLOADS}/{filename}'
            # Dataset
            nam.df = df_nam
            # Run NAM
            nam.run()
            nam.stats()
            nam.update()

            basin['basin_def']['BAHADURABAD']['nam']['umax'] = nam.parameters.x[0]
            basin['basin_def']['BAHADURABAD']['nam']['lmax'] = nam.parameters.x[1]
            basin['basin_def']['BAHADURABAD']['nam']['cqof'] = nam.parameters.x[2]
            basin['basin_def']['BAHADURABAD']['nam']['ckif'] = nam.parameters.x[3]
            basin['basin_def']['BAHADURABAD']['nam']['ck12'] = nam.parameters.x[4]
            basin['basin_def']['BAHADURABAD']['nam']['tof'] = nam.parameters.x[5]
            basin['basin_def']['BAHADURABAD']['nam']['tif'] = nam.parameters.x[6]
            basin['basin_def']['BAHADURABAD']['nam']['tg'] = nam.parameters.x[7]
            basin['basin_def']['BAHADURABAD']['nam']['ckbf'] = nam.parameters.x[8]
            basin['basin_def']['BAHADURABAD']['nam']['csnow'] = nam.parameters.x[9]
            basin['basin_def']['BAHADURABAD']['nam']['snowtemp'] = nam.parameters.x[10]

            with open(basin_file, 'w') as basin_file_write_buffer:
                json.dump(basin, basin_file_write_buffer, indent=2)

            statistics['NAM'] = dict(
                NSE=nam.NSE,
                RMSE=nam.RMSE
            )

            with open(statistics_file, 'w') as stat_file_write_buffer:
                json.dump(statistics, stat_file_write_buffer, indent=2)

            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v2/data/nam/<string:filename>/predict', methods=['POST'])
    def predictNamModel(filename: str):
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

            df_nam = pd.DataFrame(dict(
                Date=time,
                Temp=[0]*len(time),
                Q=[0]*len(time),
                P=prec,
                E=et
            ))
            df_nam = df_nam.set_index('Date')

            project = ioh.read_project_file(
                f"{UPLOADS}/{filename}/{filename}.project.json")

            basin_file = f"{UPLOADS}/{filename}/{project['basin']}"
            del_t_proj = project['interval']

            basin = ioh.read_basin_file(basin_file)
            area = basin['basin_def']['BAHADURABAD']['area']
            parameter = basin['basin_def']['BAHADURABAD']['nam']

            nam_model = Nam(
                Filename=filename, Area=area, Cal=False, DeltaT=del_t_proj)
            nam_model.initial = [parameter['umax'], parameter['lmax'], parameter['cqof'], parameter['ckif'], parameter['ck12'],
                                 parameter['tof'], parameter['tif'], parameter['tg'], parameter['ckbf'], parameter['csnow'], parameter['snowtemp']]
            nam_model.df = df_nam
            nam_model.run()

            df_nam['Qsim'] = nam_model.Qsim
            df_nam['Time'] = df_nam.index
            df_nam = df_nam.drop(['Temp', 'Q'], axis=1)
            result = df_nam.to_dict(orient='records')

            res = jsonify({'message': 'ok', 'result': result})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
