from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f:
    readme = f.read()



setup(
    name='ntripclient',
    version='0.0.1',

    author='Michael Perna',
    author_email='michael.perna@alumni.epfl.ch',
    packages=['ntripbrowser'],
    install_requires=[],
    tests_requires=['pytest', 'mock', 'tox'],
    license='',
    url='git',
    description='CLI tool to establish NTRIP client server',
    long_description=readme,
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            'myscript=ntripclient:run'
        ]
    }
)