from subprocess import call

call('nosetests --with-doctest btc/*.py', shell=True)
