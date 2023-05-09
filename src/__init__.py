from flask import Flask
from flask_cors import CORS

from route_user import getRouteUser
from route_tank import getRouteTank
from route_nam import getRouteNam
from project_config import PORT

# Flask Server Backend
app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


# Router
getRouteUser(app)
getRouteTank(app)
getRouteNam(app)


# Start Backend
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT)
