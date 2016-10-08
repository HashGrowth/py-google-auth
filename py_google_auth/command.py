'''
Implements command line interface for the API.
This will be used to run the API server.


Usage:
  py_google_auth [<address>]
  py_google_auth -V | --version
  py_google_auth -h | --help

Where:
  <address> is what to listen on, of the form <host>[:<port>], or just <port>
'''

import logging
import optparse
import re
import subprocess
import sys

with open('py_google_auth/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)


usage = '\n\n\n'.join(__doc__.split('\n\n\n')[1:])
version = 'py-google-auth ' + version


def get_address(arguments):
    '''
    Function to resolve listen address for server.
    '''
    if not arguments:
        host = 'localhost'
        port = '8001'

    elif len(arguments) == 1:
        host = 'localhost'
        try:
            port = str(int(sys.argv[1]))
        except ValueError:
            logging.error("\n\nInvalid Port.\n")
            sys.exit(1)

    elif len(arguments) == 2:
        host = sys.argv[1]
        try:
            port = str(int(sys.argv[2]))
        except ValueError:
            logging.error("\n\nInvalid Port.\n")
            sys.exit(1)

    return host, port


def serve(host, port):
    '''
    Function to run the server.
    '''

    command_to_run_server = "gunicorn -b {host}:{port} py_google_auth.app:app".format(
        host=host, port=port)
    subprocess.call(command_to_run_server, shell=True)


def main(argv=None):
    '''
    Function to handle command line interface.
    '''

    parser = optparse.OptionParser(description='API for login into Google account',
                                   prog='py_google_auth',
                                   version=version,
                                   usage=usage)

    parser.add_option('--verbose', '-v',
                      action='store_true',
                      help='prints verbosely',
                      default=False)

    options, arguments = parser.parse_args()

    host, port = get_address(arguments)
    logging.log(1, "Listening on %s:%s" % (host, port))

    try:
        serve(host, port)
        return 0

    except Exception as e:
        print(e)
        return 1
