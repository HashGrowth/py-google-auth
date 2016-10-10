import falcon
import json
import jsonpickle
import os

from . import utils
from . import login_utils
from . import step_two_utils
from . import change_method_utils


def verify_data_exist(req, resp, resource, params):
    '''
    Verify if payload was sent with request.
    '''

    body = req.stream.read()
    try:
        data = json.loads(body.decode('utf-8'))
        req.stream = data
    except ValueError:
        raise falcon.HTTPBadRequest('Empty payload', 'No valid json was supplied with request')


def verify_credentials(req, resp, resource, params):
    '''
    Decorator method to verify whether email and password are present in data and also the email
    is valid or not.
    '''

    data = req.stream

    # extract required parameters from the data.
    try:
        email = data['email']
        data['password']
    except KeyError:
        msg = "Either email or password is not present or the email is invalid."
        raise falcon.HTTPBadRequest('Incomplete credentials', 'Please supply valid crendetials.')

    if not login_utils.is_valid_email(email):
        msg = 'This email address does not exist.'
        raise falcon.HTTPUnauthorized('Invalid credentials', msg, False)


def validate_request(req, resp, resource, params):
    '''
    Decorator method to validate token before processing request.
    '''
    # read request body and parse it into a json object.
    data = req.stream

    # token to grant access to API
    # this is set in the environment of the system where API is deployed.
    valid_token = os.environ.get('PY_GOOGLE_AUTH_TOKEN')

    if 'token' not in data:
        msg = 'Please send access token along with your request'
        raise falcon.HTTPBadRequest('Token Required', msg)
    else:
        # token received from the request data.
        req_token = data['token']

        if req_token != valid_token:
            msg = 'Please supply a valid token.'
            raise falcon.HTTPBadRequest('Invalid Token', msg)

    # since stream is a file, it has been read once so won't be able to read it again in the end
    # point functions that are called afterwards, so setting it to the data that was already parsed
    # so that it is available in the functions that follows.
    req.stream = data


@falcon.before(verify_data_exist)
@falcon.before(validate_request)
@falcon.before(verify_credentials)
class NormalLogin(object):
    '''
    Handles initial login request.
    '''
    def on_post(self, req, resp):

        # set in the decorator method for request validation.
        data = req.stream

        email = data['email']
        password = data['password']

        # call the function to make initial login attempt.
        response, error, session = login_utils.login(email, password)

        # if two factor auth detected
        if error and error == "TFA":

            # find the default tfa method
            default_method, method_error = login_utils.get_default_method(response.text)

            # if many attempts are made to login then default_method is usually blocked for a while
            # hence we don't send default_method in response so that user can select alternative
            # for which we send a list of other enabled methods on the account.
            # if it is false, we send default_method in response.
            if not method_error:
                # create payload from response text
                payload = utils.make_payload(response.text)

                # current response url is used to make next POST call for second step of login and
                # payload contains parameters that are to be sent with POST request, since we need
                # these in the function that is called on step two end point, we save it in the
                # session object and send in response so that we get it back with next request.

                session.next_url = response.url
                session.prev_payload = payload

                # Google prompt need two variables from the response page which are used to make
                # POST request to an api where prompt's respose is recorded to know what user has
                # responded for prompt. saving them into query_params.
                if default_method == 1:
                    query_params = utils.get_query_params(response.text)
                    session.query_params = query_params

            # collect all enabled methods on a user's google account.
            methods, select_method_url, error, session = login_utils.select_alternate_method(
                session, response.url)

            if not error:
                # save url to select methods, this is used to again get the form of method
                # selection which will in turn give appropriate payload for selected method
                session.select_method_url = select_method_url

            # encode session as json; details in the function itself.
            session = utils.serialize_session(session)

            # if both default_method and available methods not fetched, that is some exception
            # occured in making requests or format of the response page has changed then respond
            # with a 500 to indicate that the request can't be fulfilled. Requires updates in API
            # implementation.
            if method_error and error:
                resp.status = falcon.HTTP_500

            # if available methods not fetched; return default_method only
            elif error:
                resp.status = falcon.HTTP_502
                resp.body = json.dumps({'session': session, 'default_method': default_method})

            # if default method not available; return all enabled methods
            elif method_error:
                resp.status = falcon.HTTP_503
                resp.body = json.dumps({'session': session, 'methods': methods})

            else:
                # if both default method and available methods fetched
                resp.status = falcon.HTTP_303
                resp.body = json.dumps({'session': session, 'default_method': default_method,
                                        'methods': methods})

        elif error and error == "Connection Error":
            resp.status = falcon.HTTP_504

        # Parsing error is same throughout the implementation which indicates that API needs update
        # in its implementation.
        elif error and error == "Parsing Error":
            resp.status = falcon.HTTP_500

        elif error and error == "Invalid credentials":
            resp.status = falcon.HTTP_401

        # Too many login attempts can throw captcha, in this case we need to rout the request to
        # another server (if deployed in big scale where multiple servers are available to handle
        # this part else just try after some time).
        elif error and error == "captcha":
            pass

        else:
            # encode session as json; this is different from the encoding process used above when
            # two factor auth was detected, here no extra variables are stuffed so it is directly
            # encoded into json and sent back.
            session = jsonpickle.encode(session)

            # if no two factor auth detected
            resp.status = falcon.HTTP_200
            resp.body = json.dumps({'session': session})


@falcon.before(verify_data_exist)
@falcon.before(validate_request)
class StepTwoLogin(object):
    '''
    Handles two factor authentication.
    '''
    def on_post(self, req, resp):

        # set in the decorator method for request validation.
        data = req.stream

        # extract required parameters from the data.
        method = data['method']
        session = data['session']

        # deserialize session into an object from the string.
        session = utils.deserialize_session(session)

        # if method is google prompt then no otp is avaiable in the request.
        if method != 1:
            otp = data['otp']
            query_params = None

        # but query_params are present in the session object which were stuffed in previous call to
        # the API.
        else:
            otp = None
            query_params = session.query_params

        # extract other variables that were stuffed in previous call to the API.
        tfa_url = session.next_url
        payload = session.prev_payload

        # remove the variables from the session object so as to make it a normal requests.Session
        # object.
        session = utils.clean_session(session)

        # make the login attempt for second step of authentication
        response, error, session = step_two_utils.second_step_login(session, method, tfa_url,
                                                                    payload, query_params, otp)

        # since no further requests will be made in sequence after this request so no extra
        # variables are stuffed hence normal json encoding works here for the session object.
        session = jsonpickle.encode(session)

        if error:
            if error == "Connection Error":
                resp.status = falcon.HTTP_504

            elif error == "Parsing Error":
                resp.status = falcon.HTTP_500

            elif error == "Wrong Code" or error == "Empty Code":
                resp.status = falcon.HTTP_406

            elif error == "Prompt Denied":
                resp.status = falcon.HTTP_412

            elif error == "Time Out":
                resp.status = falcon.HTTP_408

            else:
                resp.status = falcon.HTTP_200

        resp.body = json.dumps({'session': session})


@falcon.before(verify_data_exist)
@falcon.before(validate_request)
class ChangeMethod(object):
    '''
    Handle changing the two factor method.
    '''
    def on_post(self, req, resp):

        # set in the decorator method for request validation.
        data = req.stream

        # extract required parameters from the data.
        method = data['method']
        session = data['session']

        # deserialize session into an object from the string.
        session = utils.deserialize_session(session)

        # extract other variables that were stuffed in previous call to the API.
        select_method_url = session.select_method_url

        # remove the variables from the session object so as to make it a normal requests.Session
        # object.
        session = utils.clean_session(session)

        # get response for url and payload for next request for the selected method; in this
        # function, a POST request is made to a url ( which is prepared according to the selected
        # method) and which in turn sends otp or prompt to user.
        response, error, session = change_method_utils.get_alternate_method(session, method,
                                                                            select_method_url)
        # data to send back
        data = {}

        if error:
            if error == "Connection Error":
                resp.status = falcon.HTTP_504

            elif error == "Parsing Error":
                resp.status = falcon.HTTP_500
        else:
            # get the method code, this is done so that the api user can get the method code to
            # send back in the next call to step two end point.
            method = change_method_utils.get_method_for_selection(method)

            # payload for next request
            payload = utils.make_payload(response.text)

            # stuffing data for next request from the user; explained in detail in class `Login`.
            session.next_url = response.url
            session.prev_payload = payload

            data['method'] = method

            resp.status = falcon.HTTP_200

        # encode session as json; need to call the serialize function because again extra variables
        # are being stuffed in the session.
        session = utils.serialize_session(session)
        data['session'] = session

        resp.body = json.dumps(data)
