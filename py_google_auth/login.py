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
        raise falcon.HTTPBadRequest('Incomplete credentials', msg)

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
        if error and error == 303:

            # find the default tfa method
            response_default, error_default = login_utils.get_default_method(response.text)

            # collect all enabled methods on a user's google account.
            response_alternate, error_alternate, session = login_utils.select_alternate_method(
                session, response.url)

            response_data = {}

            # if both default_method and available methods not fetched, that is some exception
            # occured in making requests or format of the response page has changed then respond
            # with a 500 to indicate that the request can't be fulfilled. Requires updates in API
            # implementation.
            if error_default and error_alternate:
                resp.status = falcon.HTTP_500
                resp.body = json.dumps(response_default)

            # if available methods not fetched; return default_method only
            elif error_alternate:
                # from get_default_method response, we extract default method
                default_method = response_default['method']

                # set variables in session and prepare response using a utility method
                response_data, session = utils.handle_default_method(default_method,
                                                                     response, session)

                # encode session as json; details in the function itself.
                session = utils.serialize_session(session)
                response_data['session'] = session

                resp.status = falcon.HTTP_502
                resp.body = json.dumps(response_data)

            # if default method not available; return all enabled methods
            elif error_default:
                select_method_url = response_alternate['select_method_url']
                methods = response_alternate['methods']

                # save url to select methods, this is used to again get the form of method
                # selection which will in turn give appropriate payload for selected method
                session.select_method_url = select_method_url

                # encode session as json; details in the function itself.
                session = utils.serialize_session(session)

                response_data['methods'] = methods
                response_data['session'] = session

                resp.status = falcon.HTTP_503
                resp.body = json.dumps(response_data)

            else:
                # if both default method and available methods fetched

                # from get_default_method response, we extract default method
                default_method = response_default['method']

                select_method_url = response_alternate['select_method_url']
                methods = response_alternate['methods']

                response_data, session = utils.handle_default_method(default_method,
                                                                     response, session)

                # save url to select methods, this is used to again get the form of method
                # selection which will in turn give appropriate payload for selected method
                session.select_method_url = select_method_url

                # encode session as json; details in the function itself.
                session = utils.serialize_session(session)

                response_data['methods'] = methods
                response_data['session'] = session

                resp.status = falcon.HTTP_303
                resp.body = json.dumps(response_data)

        elif error and error == 504:
            resp.status = falcon.HTTP_504

        elif error and error == 401:
            resp.status = falcon.HTTP_401

        # Too many login attempts can throw captcha, in this case we need to rout the request to
        # another server (if deployed in big scale where multiple servers are available to handle
        # this part else just try after some time).
        elif error and error == 429:
            resp.status = falcon.HTTP_429

        # Any other error indicates that API needs update in its implementation.
        elif error:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps(response)

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

        response_data = {}

        if error:
            if error == 504:
                resp.status = falcon.HTTP_504

            elif error == 400:
                msg = "Send a valid method code"
                raise falcon.HTTPBadRequest('Invalid Method', msg)

            elif error == 406:
                resp.status = falcon.HTTP_406

            elif error == 412:
                resp.status = falcon.HTTP_412

            elif error == 408:
                resp.status = falcon.HTTP_408

            elif error == 503:
                url = response['url']
                methods = response['methods']

                # save the url from where list of methods was obtained, this will be used to
                # collect payload in next request when a method will be selected
                session.select_method_url = url
                session = utils.serialize_session(session)

                response_data['methods'] = methods
                resp.status = falcon.HTTP_503

            elif error == 502:
                methods = utils.get_method_names()
                default_method = [m for m in methods if methods[m][1] in response.url][0]

                # set variables in session and prepare response using a utility method
                response_data, session = utils.handle_default_method(default_method,
                                                                     response, session)
                session = utils.serialize_session(session)
                response_data['default_method'] = default_method
                resp.status = falcon.HTTP_502

            elif error == 506:
                # using this way because no falcon status codes suits the purpose.
                resp.status = "506"
                session = utils.serialize_session(session)

            else:
                resp.status = falcon.HTTP_500
                response_data = response

        else:
            resp.status = falcon.HTTP_200

        # 502 and 503 shows that too many attempts with wrong otp were made, so in this case we
        # either fall back to default method or provide a list of methods to select from (when
        # default is blocked)
        if error != 503 and error != 502:
            session = jsonpickle.encode(session)

        response_data['session'] = session
        resp.body = json.dumps(response_data)


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
        response_data = {}

        if error:
            if error == 504:
                resp.status = falcon.HTTP_504

            elif error == 400:
                msg = "Send a valid method"
                raise falcon.HTTPBadRequest("Invalid Method", msg)

            else:
                resp.status = falcon.HTTP_500
                response_data = response

        else:
            # if method is text message, extract the phone number from it.
            if "text message" in method:
                phone_num = change_method_utils.extract_phone_num(method)
                response_data['number'] = phone_num

            # get the method code, this is done so that the api user can get the method code to
            # send back in the next call to step two end point.
            method = change_method_utils.get_method_for_selection(method)

            # payload for next request
            payload = utils.make_payload(response.text)

            # stuffing data for next request from the user; explained in detail in class `Login`.
            session.next_url = response.url
            session.prev_payload = payload

            response_data['method'] = method

            resp.status = falcon.HTTP_200

        # encode session as json; need to call the serialize function because again extra variables
        # are being stuffed in the session.
        session = utils.serialize_session(session)
        response_data['session'] = session

        resp.body = json.dumps(response_data)
