from flask import Flask
from flask_cors import CORS
from routes.api import api_bp
from routes.auth import auth_bp
import os

app = Flask(__name__)

# Habilitar CORS para todas las rutas y orígenes
CORS(app)

# Registrar el Blueprint
app.register_blueprint(api_bp, url_prefix='/api')

# Registrar las nuevas rutas de autenticación
app.register_blueprint(auth_bp, url_prefix='/auth')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)