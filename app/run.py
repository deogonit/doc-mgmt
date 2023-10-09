from newrelic.agent import initialize as nr_initialize

nr_initialize("./setup.cfg")

from newrelic.agent import application as nr_application

nr_application().activate()

from app.main import app
