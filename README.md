# py-google-auth

## Introduction
An api to log into a user's Google account using their email and password.

## Set up for testing

* Create Virtual Environment  
(_Note: Make sure you have python [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) and [virtualenvwrapper](http://docs.python-guide.org/en/latest/dev/virtualenvs/) installed_)        

        mkvirtualenv -p `which python3.4` py-google-auth

* Clone the repository        

        git clone https://github.com/HashGrowth/py-google-auth.git py-google-auth

* Install requirements        

        pip install -r requirements.txt

* Set an environment variable for logs, run this on terminal        

        "export PY_GOOGLE_AUTH_LOG_PATH=/path/to/logs" >> ~/.bashrc

* Set an access token for API        

        "export PY_GOOGLE_AUTH_TOKEN='some_token'" >> ~/.bashrc

* Run API server in a seperate terminal        

        gunicorn -b localhost:8001 app

## End points

**_Note:_**: _`token` with every request is the same as the value of `$PY_GOOGLE_AUTH_TOKEN`_

### Normal login

Request:    

    resp = requests.post('http://localhost:8001/login', data=json.dumps({"token": token, "email": email, "password": password}))

Response:    

    response = resp.json()

response structure:    

    response = data

_status codes_:

* success : 200
* tfa : 303
* connection error : 504
* parsing error : 500
* Invalid credentials: 400
* default_method not available : 503
* list of methods not available : 502

_data_:

* **success** - {'session': session}
* **tfa** - {'session': session, 'default_method': default_method_code, 'available_methods': available_methods}
* **error** - No data
* **default_method not available** - {'session': session, 'available_methods': available_methods}
* **list of methods not available** - {'session': session, 'default_method': default_method_code}

_Default Method Codes_:

* 1 : Google Prompt
* 2 : Google Authenticator Code
* 3 : Text Message OTP
* 4 : Backup code
* 5 : Google Support



### Two step login

Request:    

    resp = requests.post('http://localhost:8001/step_two_login', data=json.dumps({"token": token, "method": method, "otp": otp, "session": session}))

Response:    

    response = resp.json()

response structure:    

    response = {'session': session}

_status codes_:

* success : 200
* connection error : 504
* parsing error : 500
* wrong otp error : 406
* prompt denied : 412
* time out : 408


### Alternate Method Selection

Request:    

    resp = requests.post('http://localhost:8001/change_method', data=json.dumps({"token": token, "method": method, "session": session}))

Response:    

    response = resp.json()

response structure:    

    response = {'session': session}

_status codes_:

* success : 200
* connection error : 504
* parsing error : 500
