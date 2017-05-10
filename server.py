from flask import abort, Flask

from parser import get_events

application = Flask(__name__)


@application.route("/")
def serve():
    return get_events()


if __name__ == "__main__":
    application.run()
