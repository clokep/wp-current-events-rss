from flask import Flask

from parser import get_articles

application = Flask(__name__)


@application.route("/")
def serve():
    return get_articles()


if __name__ == "__main__":
    application.run()
