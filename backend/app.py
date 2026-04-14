import os
from flask import Flask, jsonify
from flask_cors import CORS
from extensions import db
from routes.health import health_bp
from routes.predict import predict_bp
from routes.predictions_history import predictions_history_bp
from routes.dashboard import dashboard_bp
from routes.analysis import analysis_bp


def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)

    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(basedir, "predictions.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(predictions_history_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analysis_bp)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

@app.route("/")
def index():
    return jsonify({"message": "Welcome to the Aviation Intelligence API"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
