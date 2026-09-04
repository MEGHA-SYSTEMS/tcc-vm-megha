import os
import firebase_admin
from firebase_admin import credentials
from flask import Flask

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = 'super_secret_key'

try:
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        except Exception:
            firebase_admin.initialize_app()
        except Exception as e:
            print("Atenção: Firebase não foi inicializado corretamente.", e)
            
            from app.controllers.home_controller import home_bp
            from app.controllers.auth_controller import auth_bp
            
            app.register_blueprint(home_bp)
            app.register_blueprint(auth_bp)
            
            return app 