py-google-auth
==============

Login into a Google account using Python.

py-google-auth is a Python library which provides an API for login a Google account.
Also able to detect and perform two step authentication if enabled.

Installation
------------

To install, run:
 
.. code-block:: bash

    $ pip install py-google-auth

(for test):
.. code-block:: bash

    $ pip install -i https://testpypi.python.org/pypi --extra-index-url https://pypi.python.org/pypi py-google-auth

To be able to make requests to API, you will need a token.
You need to set it in your system environment for the API to access it and then pass it with every request you make:   

.. code-block:: bash

    export PY_GOOGLE_AUTH_TOKEN='some_token'

Also set a path for storing log files.
These files will be created when ever some previously unhandled error will occur,
in order to help debugging and fixing the problem. You can create a PR for such errors with the content of the file from your log path:    

.. code-block:: bash

    export PY_GOOGLE_AUTH_LOG_PATH=/path/to/logs/

Usage
-----

Open your terminal and run:

.. code-block:: bash

    py_google_auth

This will start a gunicorn server, which will listen on `localhost:8001` by default. You can change host and port (run `py_google_auth -h` for information).

Then you can make calls to the api using any HTTP library you like.
The `docs <http://py-google-auth.readthedocs.io/en/latest/>`_ will contain examples with `requests <https://github.com/kennethreitz/requests>`_.

Example for an account without two factor auth enabled:

.. code-block:: python

    >>> import jsonpickle
    >>> import os
    >>> import requests

    >>> token = os.environ.get('PY_GOOGLE_AUTH_TOKEN')
    >>> data = {'email': 'myemail@example.com', 'password': 'myrandompassword', 'token': token}

    >>> req = requests.post('http://localhost:8001/login', json=data}
    >>> req
    <Respose 200>

    >>> session_str = req.json()['session']
    >>> session = jsonpickle.decode(session_str)
    >>> google_play_page = session.get('https://play.google.com/apps/publish')
    >>> google_play_page
    <Respose 200>

More examples with other endpoints can be found in `docs <http://py-google-auth.readthedocs.io/en/latest/>`_.


End points
----------

Normal login (without two factor auth).

.. code-block:: bash

    POST /login --data {'email': email, 'password': password, 'token': token}

If two factor auth is enabled, then next request should go here:

.. code-block:: bash

    POST /step_two_login --data {'session': session, 'method': method, 'otp': otp, 'token': token}

If you want to use alternate method for two factor, use this before `/step_two_login`:

.. code-block:: bash

    POST /change_method --data {'session': session, 'method': method, 'token': token}

Details about response data and status codes can be found in `docs <http://py-google-auth.readthedocs.io/en/latest/>`_.

Documentation
-------------

Documentation can be found at `http://py-google-auth.readthedocs.io/en/latest/`, writing in process.
