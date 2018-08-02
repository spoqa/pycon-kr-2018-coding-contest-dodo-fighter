from setuptools import setup, find_packages

setup(
    name='pycon2018',
    version='0.0.1',
    description='PyCon KR 2018 coding event',
    packages=find_packages(exclude=['migration', 'migration.*']),
    scripts=['scripts/script_runner']
)
