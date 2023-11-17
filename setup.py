from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

packages = ['flask_dictabase']

setup(
    name="flask_dictabase",

    version="1.2.5",
    # 1.2.5 - feat: when using BaseTable.Remove(key, x), an error will NOT be thrown if x is not in the list
    # 1.2.4 - Added a BaseTable().uuid, so each row is auto-assigned a UUID
    # 1.2.3 - Added Dictabase.FindAll(Table, _where='age', _greaterThan=18, __where='weight', __greaterThan=100)
    # 1.2.2 - Added Dictabase.FindAll(Table, _where='age', _greaterThan=18)
    # 1.2.1 - Added BaseTable.Update to account for unsupported values
    # 1.2.0 - Added BaseTable.Link()/Unlink()/Links() to easily link rows to each other across tables (relationships?)
    # 1.1.6 - Added 'allowDuplicates' to BaseTable.Append() and 'removeAll' to BaseTable.Remove()
    # 1.1.5 - Added Variables so act like global variables, but stored in db
    # 1.1.4 - Added NewOrFind() which will create a new obj if it is not found
    # 1.1.2 - Added .GetItem()
    # 1.1.0 - Added .Remove() and .PopItem()
    # 1.0.16 - Issues with .Set() not committing to db ?
    # 1.0.12 - Added with self.db.lock and WaitForTransactionsToComplete to FindOne and FindAll to prevent error "sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked"
    # 1.0.10 - Added BaseTable.app so you can easily access the app from inside a BaseTable object method
    # 1.0.9 - Added helper methods to BaseTable: Append() and SetItem()
    # 1.0.8 - New(), FindOne() and FindAll() can now pass str or class as first arg
    # 1.0.7 - Added BaseTable Set/Get methods to help deal with unsuported db types

    packages=packages,
    install_requires=[
        'flask',
        'dataset',
    ],

    author="Grant miller",
    author_email="grant@grant-miller.com",
    description="A dict() like interface to your database.",
    long_description=long_description,
    license="PSF",
    keywords="grant miller flask database",
    url="https://github.com/GrantGMiller/flask_dictabase",  # project home page, if any
    project_urls={
        "Source Code": "https://github.com/GrantGMiller/flask_dictabase",
    }

)
''' To upload the changes to PyPI, run this command in terminal

python -m setup.py sdist bdist_wheel
twine upload /Users/grantmiller/PycharmProjects/flask_dictabase/dist/* --username myUserName --password mySecretPassword

'''