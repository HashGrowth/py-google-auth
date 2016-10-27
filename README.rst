py-google-auth
==============

Headless implementation of Google web login (with support for 2-Step Verification) in Python

`py-google-auth` exposes a high-level Python module and REST API that can be used for headless login on `Google Accounts <https://accounts.google.com/ServiceLogin>`_. The API supports *2-step verification* if it is enabled on Google Account being used.

**Note**: This project is in "alpha" version right now.
We are actively developing it and expect it to be beta-ready in next couple of weeks.

License
-------
MIT

The license text is available in `LICENSE` file in root of this repo.


Installation
------------

To install, run:
 
.. code-block:: bash

    $ pip install py-google-auth

(for test):

.. code-block:: bash

    $ pip install -i https://testpypi.python.org/pypi --extra-index-url https://pypi.python.org/pypi py-google-auth

to update the version:

.. code-block:: bash

    $ pip install -Ui https://testpypi.python.org/pypi --extra-index-url https://pypi.python.org/pypi py-google-auth

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

    py-google-auth

This will start a gunicorn server, which will listen on ``localhost:8001`` by default. You can change host and port (run ``py-google-auth -h`` for information).

Then you can make calls to the api using any HTTP library you like.
The `docs <http://py-google-auth.readthedocs.io/en/latest/>`_ will contain examples with `requests <https://github.com/kennethreitz/requests>`_.

Example for an account without two factor auth enabled:

.. code-block:: python

    >>> import jsonpickle
    >>> import os
    >>> import requests

    >>> token = os.environ.get('PY_GOOGLE_AUTH_TOKEN')
    >>> data = {'email': 'myemail@example.com', 'password': 'myrandompassword', 'token': token}

    >>> req = requests.post('http://localhost:8001/login', json=data)
    >>> req
    <Respose 200>

    >>> session_str = req.json()['session']
    >>> session = jsonpickle.decode(session_str)
    >>> google_play_page = session.get('https://play.google.com/apps/publish')
    >>> google_play_page
    <Respose 200>


*Note:* ``jsonpickle`` is used to encode python objects into json, since we get an encoded string which contains a request.Session object, we need to use decode to make it an object again.

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

Supported 2-step verification 'steps'
-------------------------------------

We support following 'steps' (i.e. methods) offered by Google in `2-step verification <https://myaccount.google.com/security/signinoptions/two-step-verification>`_:

* **Voice or text message**: Verification codes are sent by text message.
* **Backup codes**: 10 single-use codes are active at this time, but you can generate more as needed.
* **Google prompt**: Get a Google prompt on your phone and just tap Yes to sign in.
* **Authenticator app**: Use the Authenticator app to get free verification codes, even when your phone is offline. Available for Android and iPhone.
* **Backup phone**: Add a backup phone so you can still sign in if you lose your phone.

Unsupported 2-step verification 'step'
--------------------------------------
We **DONT** support following 'step' (i.e. method):

* **Security Key**: A Security Key is a small physical device used for signing in. It plugs into your computer's USB port.

Documentation
-------------

We are in process of writing documentation, which will be hosted at `http://py-google-auth.readthedocs.io/en/latest/ <http://py-google-auth.readthedocs.io/en/latest/>`_.

FAQs
----
To be done.

Maintainers/Contact
-------------------

* `Swati Jaiswal <https://github.com/curioswati>`_ (Current maintainer)
* If Swati isn't responding, feel free to poke `Amber Jain <https://github.com/amberj>`_ or `Pulkit Vaishnav <https://github.com/pulkitvaishnav/>`_.

How to Contribute
-----------------
1. Check for `open issues or open a fresh issue <https://github.com/HashGrowth/py-google-auth/issues>`_ to start a discussion around a feature idea or a bug.
2. Fork the repository on GitHub to start making your changes to the master branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and poke the maintainer until it gets merged and published :)
