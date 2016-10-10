import os
import re

from codecs import open
from setuptools import setup, find_packages

packages = [
    'py_google_auth'
]

requires = [
    'BeautifulSoup4',
    'falcon',
    'gevent',
    'gunicorn',
    'jsonpickle',
    'requests'
]

with open('py_google_auth/version.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')


def read(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()

setup(
    name='py-google-auth',
    version=version,
    description='API for login into a google account.',
    long_description=read("README.rst"),
    author='Swati Jaiswal',
    author_email='jaiswalswati94@gmail.com',
    url='https://github.com/HashGrowth/py-google-auth/',
    packages=find_packages(),
    package_data={'': ['LICENSE']},
    package_dir={'py_google_auth': 'py_google_auth'},
    include_package_data=True,
    install_requires=requires,
    license='MIT License',
    zip_safe=False,
    classifiers=(
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        ),
    keywords='google login auth',
    entry_points={'console_scripts': ['py_google_auth = py_google_auth:main']},
)
