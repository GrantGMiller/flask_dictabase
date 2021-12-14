import random
import string

from flask import (
    Flask,
    request,
)
import flask_dictabase

app = Flask('User Management')
# if you would like to specify the SQLAlchemy database then you can do:
# app.config['DATABASE_URL'] = 'sqlite:///my.db'
app.db = flask_dictabase.Dictabase(app)


@app.route('/set/<key>/<value>')
def Set(key, value):
    app.db.var.Set(key, value)
    return f'Set {key}={value}'


@app.route('/get/<key>')
def Get(key):
    return app.db.var.Get(key)


if __name__ == '__main__':
    app.run(debug=True)
