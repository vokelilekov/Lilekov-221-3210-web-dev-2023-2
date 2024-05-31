from flask import Flask
from flask_login import LoginManager
from app.mysqldb import DBConnector

app = Flask(__name__, template_folder='templates')
application = app
app.config.from_pyfile('config.py')

db_connector = DBConnector(app)

from app.reports.reports import reports_bp
app.register_blueprint(reports_bp, url_prefix='/reports')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Войдите, чтобы просматривать содержимое данной страницы"
login_manager.login_message_category = "warning"
