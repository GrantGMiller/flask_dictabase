Flask-Dictabase
===============
A dict() like interface to your database.

Install
=======
::

    pip install flask_dictabase

Here is a simple flask app implementation.
::

    import random
    import string

    from flask import (
        Flask,
        render_template,
        redirect
    )
    import flask_dictabase

    app = Flask('User Management')
    # if you would like to specify the SQLAlchemy database then you can do:
    # app.config['DATABASE_URL'] = 'sqlite:///my.db'
    db = flask_dictabase.Dictabase(app)


    class UserClass(flask_dictabase.BaseTable):
        pass


    @app.route('/')
    def Index():
        return render_template(
            'users.html',
            users=db.FindAll(UserClass),
        )


    @app.route('/update_user_uption/<userID>/<state>')
    def UpdateUser(userID, state):
        newState = {'true': True, 'false': False}.get(state.lower(), None)
        user = db.FindOne(UserClass, id=int(userID))
        user['state'] = newState # This is immediately saved to the database.
        return redirect('/')


    @app.route('/new')
    def NewUser():
        email = ''.join([random.choice(string.ascii_letters) for i in range(10)])
        email += '@'
        email += ''.join([random.choice(string.ascii_letters) for i in range(5)])
        email += '.com'

        newUser = db.New(UserClass, email=email, state=bool(random.randint(0, 1)))
        print('newUser=', newUser) # This is now immediately saved to the database.
        return redirect('/')


    @app.route('/delete/<userID>')
    def Delete(userID):
        user = db.FindOne(UserClass, id=int(userID))
        print('user=', user)
        if user:
            db.Delete(user) # User is now removed from the database.
        return redirect('/')


    if __name__ == '__main__':
        app.run(
            debug=True,
            threaded=True,
        )

Unsupported Types
=================
If you want to store more complex information like list() and dict(), you can use the .Set() and .Get() helper methods.
These convert your values to/from json to be stored in the db as a string.

::

    myList = [1,2,3,4,5] #
    user = db.FindOne(UserClass, id=1)
    if user:
        user.Set('myList', myList)

    user2 = db.FindOne(UserClass, id=1)
    print('user2.Get('myList')=', user2.Get('myList'))

Output
::

    >>> user2.Get('myList')= [1, 2, 3, 4, 5]

You can also use a different function to load/dump the values. Like python's pickle module.
::

    import pickle
    myList = [1,2,3,4,5] #
    user = db.FindOne(UserClass, id=1)
    if user:
        user.Set('myList', myList, dumper=pickle.dumps, dumperKwargs={})

    user2 = db.FindOne(UserClass, id=1)
    print('user2.Get('myList')=', user2.Get('myList', loader=pickle.loads))

You can also provide a default argument to .Get()
::

    user = db.FindOne(UserClass, id=1)
    user.Get('missingKey', None) # return None if key is missing, else return the dumped value

Gunicorn
========

Supports multiple workers (-w config option).
Example::

    gunicorn main:app -w 4 -b localhost:8080
