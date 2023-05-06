import json
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from tank_model.tank_core import io_helpers as ioh

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

    @app.route('/api/v2/data/nam/<string:filename>/predict', methods=['GET'])
    def getPredictNamModel(filename: str):
        try:
            res = jsonify({'message': 'ok'})
            res.status_code = 200
            return res
        except Exception as error:
            res = jsonify({'message': 'Bad request', 'content': str(error)})
            res.status_code = 400
            return res
