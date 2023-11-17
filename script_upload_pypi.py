import config
import subprocess
res0 = subprocess.check_output('python -m setup.py sdist bdist_wheel'.split(' '))
print('res0=', res0.splitlines())
res = subprocess.check_output(f'twine upload /Users/grantmiller/PycharmProjects/flask_dictabase/dist/* --username __token__ --password {config.API_TOKEN}'.split(' '))
print('res=', res.splitlines())