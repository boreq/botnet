import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='botnet',
    version='0.1.0',
    author='boreq',
    author_email='boreq@sourcedrops.com',
    description = ('IRC bot.'),
    license='BSD',
    packages=[
        'botnet',
        'botnet/modules',
        'botnet/modules/builtin',
        'botnet/modules/builtin/mumble',
        'botnet/modules/lib'
    ],
    long_description=read('README.md'),
    install_requires=[
        'blinker',
        'Click',
        'requests',
        'xmltodict',
        'protobuf',
    ],
    entry_points='''
        [console_scripts]
        botnet=botnet.cli:cli
    ''',
)
