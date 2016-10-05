# py-google-auth

## Introduction
An api to log into a user's Google account using their email and password.

## End points

### Normal login

Request:    

    POST '/api/login' --data={'token': token, 'email': email, 'password': password}

Response:    

    response = {'status': status_code, data}

_status codes_:

* success : 200
* tfa : 303
* connection error : 504
* parsing error : 500
* Invalid credentials: 401
* default_method not available : 503
* list of methods not available : 502

_data_:

* **success** - 'session': session
* **tfa** - 'session': session, 'default_method': default_method_code, 'available_methods': available_methods
* **error** - No data
* **default_method not available** - 'session': session, 'available_methods': available_methods
* **list of methods not available** - 'session': session, 'default_method': default_method_code

_Default Method Codes_:

* 1 : Google Prompt
* 2 : Google Authenticator Code
* 3 : Text Message OTP
* 4 : Backup code
* 5 : Google Support



### Two step login

Request:    

    POST '/api/step_two_login' --data={'token': token, 'session': session, 'otp': otp, 'method': method}

Response:    

    response = {'status': status_code, 'session': session}

_status codes_:

* success : 200
* connection error : 504
* parsing error : 500
* wrong otp error : 406
* prompt denied : 412
* time out : 408


### Alternate Method Selection

Request:    

    POST '/api/change_method' --data={'token': token, 'session': session, 'method': method}

Response:    

    response = {'status': status_code, 'session': session}

_status codes_:

* success : 200
* connection error : 504
* parsing error : 500
