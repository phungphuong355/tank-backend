import json
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from tank_core import io_helpers as ioh
from Nam import Nam

from project_config import HOST_DB, NAME_DB, PORT_DB, UPLOADS


def getRouteNam(app: Flask):
    # Database
    app.config["MONGO_URI"] = f"mongodb://{HOST_DB}:{PORT_DB}/{NAME_DB}"
    mongo = PyMongo(app)

    @app.route('/api/v2/data/nam/<string:filename>/getModel', methods=['GET'])
    def getNamModel(filename: str):
        try:
            res = jsonify({'message': 'ok'})
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
            nam_file = f"{UPLOADS}/{filename}/{project['nam']}"

            basin = ioh.read_basin_file(basin_file)
            nam = ioh.read_ts_file(nam_file)
            del_t_proj = project['interval']

            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v2/data/nam/<string:filename>/optimize', methods=['PATCH'])
    def optimizeNamModel(filename: str):
        try:
            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res

    @app.route('/api/v2/data/nam/<string:filename>/predict', methods=['PATCH'])
    def predictNamModel(filename: str):
        try:
            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
