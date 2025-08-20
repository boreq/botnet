import os
from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='botnet',
    version='0.1.0',
    author='boreq',
    description = ('IRC bot.'),
    long_description=read('README.md'),
    url='https://github.com/boreq/botnet/',
    license='BSD',
    packages=find_packages(),
    install_requires=[
        'blinker>=1.4',
        'Click>=2.0',
        'requests>=2.12',
        'protobuf>=3.0',
        'requests-oauthlib>=0.7.0',
        'beautifulsoup4>=4.6.0',
        'markov @ git+https://github.com/boreq/markov#egg=markov-0.0.0',
        'Mastodon.py==2.1.1',
    ],
    entry_points='''
        [console_scripts]
        botnet=botnet.cli:cli
    '''
)
