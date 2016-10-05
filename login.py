import falcon
import json
import jsonpickle

import utils
import login_utils
import step_two_utils


class NormalLogin(object):
    '''
    Handles initial login request.
    '''
    def on_post(self, req, resp):

        # parse data
        body = req.stream.read()
        data = json.loads(body.decode('utf-8'))
        email = data['email']
        password = data['password']

        response, error, session = login_utils.login(email, password)

        # if two factor auth detected
        if error and error == "TFA":

            # find the default tfa method
            default_method, method_error = login_utils.get_default_method(response.text)

            if not method_error:
                # save current response url and payload for next request
                payload = utils.make_payload(response.text)

                if default_method == '1':
                    query_params = utils.get_query_params(response.text)
                    session.q_params = query_params

                session.next_url = response.url
                session.prev_payload = payload

            # collect all available methods
            methods, select_method_url, error, session = login_utils.select_alternate_method(
                session, response.url)

            if not error:
                # save url to select methods, to make next request
                session.select_method_url = select_method_url

            # encode session as json
            session = utils.serialize_session(session)

            # if both default_method and available methods not fetched
            if method_error and error:
                resp.status = falcon.HTTP_500

            # if available methods not fetched
            elif error:
                resp.status = falcon.HTTP_502
                resp.body = json.dumps({'session': session, 'default_method': default_method})

            # if default method not available
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

        elif error and error == "Parsing Error":
            resp.status = falcon.HTTP_500

        elif error and error == "Invalid credentials":
            resp.status = falcon.HTTP_401

        elif error and error == "captcha":
            pass

        else:
            # encode session as json
            session = jsonpickle.encode(session)

            # if no two factor auth detected
            resp.status = falcon.HTTP_200
            resp.body = json.dumps({'session': session})


class StepTwoLogin(object):
    '''
    Handles two factor authentication.
    '''
    def on_post(self, req, resp):
        body = req.stream.read()
        data = json.loads(body.decode('utf-8'))

        method = data['method']
        session = data['session']
        session = utils.deserialize_session(session)

        if method != 1:
            otp = data['otp']
            q_params = None
        else:
            otp = None
            q_params = session.q_params

        tfa_url = session.next_url
        payload = session.prev_payload
        session = utils.clean_session(session)

        # second step login
        response, error, session = step_two_utils.second_step_login(session, method, tfa_url,
                                                                    payload, q_params, otp)

        # encode session as json
        session = jsonpickle.encode(session)

        if error:
            if error == "Connection Error":
                resp.status = falcon.HTTP_504

            elif error == "Parsing Error":
                resp.status = falcon.HTTP_500

            elif error == "Wrong Code":
                resp.status = falcon.HTTP_406

            elif error == "Prompt Denied":
                resp.status = falcon.HTTP_412

            elif error == "Time Out":
                resp.status = falcon.HTTP_408

            else:
                resp.status = falcon.HTTP_200

        resp.body = json.dumps({'session': session})


class ChangeMethod(object):
    '''
    Handle changing the two factor method.
    '''
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = 'success'