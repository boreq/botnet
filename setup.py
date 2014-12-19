import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='botnet',
    version='0.0.0',
    author='boreq',
    author_email='boreq@sourcedrops.com',
    description = ('IRC bot.'),
    license='BSD',
    packages=['botnet'],
    long_description=read('README.md'),
    install_requires=[
        'blinker',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        botnet=botnet.cli:cli
    ''',
)
