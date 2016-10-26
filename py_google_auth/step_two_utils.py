import json
import os
import requests


from . import utils
from . import login_utils

# directory path for storing log files in case of unhandled cases.
log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


def handle_prompt_error(response):
    '''
    This function checks for errors (if any) while using google prompt method for login.
    '''
    if "Sign-in canceled" in response.text:
        error = 412

    else:
        file_name = utils.log_error("google prompt", response.text)
        error = 500

    return error


def handle_otp_error(response, session):
    '''
    This function checks for errors (if any) while using google authenticator method for login.
    '''

    # TODO: shift these to config file
    base_url_login = "https://accounts.google.com/ServiceLogin?"
    url_auth = "https://accounts.google.com/ServiceLoginAuth?service=androiddeveloper"

    error = utils.scrap_error(response.text)

    if error and ("Wrong" in error or "Enter a code" in error):
        error = 406

    elif "Unavailable because of too many failed attempts" in response.text:
        methods, url, error, session = login_utils.select_alternate_method(session,
                                                                           response.url)

        if not error:
            response = {'methods': methods, 'url': url}
            error = 503

    elif "Resend code" in response.text:
        # sending 3 as the method code for sms otp is 3
        payload = utils.make_payload(response.text)

        # save payload so as to make request to resend otp if required
        session.resend_payload = payload
        session.resend_url = response.url

        error = 506

    elif "bc" in response.url:
        error = 502

    # TODO: temporary solution, need to find a way to find when timeout occurs
    elif url_auth == response.url or base_url_login in response.url:
        error = 408

    else:
        file_name = utils.log_error("otp", response.text)
        error = 500

    return response, error, session


def two_step_login_with_prompt(session, payload, query_params, url_to_challenge_signin):
    '''
    Method for two step authentication with Google prompt.
    Collects a key and txId from the query_params` to create a payload to send to next page,
    which awaits user confirmation from prompt.
    When User confirms, it makes a POST call to final challenge url to verify the request.
    If request was accepted, it returns the requested google service page with user logged in.

    `session`: requests.Session object.
    `url_to_challenge_signin`: the url to make final call to verify request status
    and allow/deny login.
    `query_params`: These are two parameters, one a query parameter and the other a payload item;
    used to call `await_url`.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `utils.make_payload` function.
    '''
    error = None

    # url to make a POST call to check if a user responded on prompt.
    await_url = "https://content.googleapis.com/cryptauth/v1/authzen/awaittx?alt=json&key=%s"

    # headers are necessary to specify the referer and content type else request fails.
    headers = {"Referer": url_to_challenge_signin, "Content-Type": "application/json"}

    if query_params:
        key = query_params['key']
        txId = query_params['txId']
    else:
        error = 500
        return None, error, session

    try:
        # make call to wait for user response
        reply_from_user = session.post(await_url % key, headers=headers,
                                       data=json.dumps({"txId": txId}))

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    # convert response to json.
    reply_json = json.loads(reply_from_user.content.decode('utf-8'))

    # if request payload was not json encoded.
    if 'error' in reply_json and reply_json['error']['code'] == 400:
        error = 500
        file_name = utils.log_error("second step login", json.dumps(reply_json))

    # if user does not respond for prompt; time out error
    if 'error' in reply_json and reply_json['error']['code'] == 500:
        error = 408
        return reply_json, error, session

    try:
        # parse the token from response and add to payload to make final call
        payload['token'] = reply_json['txToken']
        payload['action'] = 'VERIFY'

        # subAction is a parameter used in previous POST/GET request so we need to remove
        # it so that we don't get redirected to previous request.
        payload.pop('subAction')

    except:
        # if there is some problem with payload, log the content of response to debug
        file_name = utils.log_error("second step login", reply_from_user.text)
        error = 500
        return reply_from_user, error, session

    try:
        # make final call to sign in
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    return resp_page, error, session


def two_step_login_with_authenticator(session, payload, url_to_challenge_signin, code):
    '''
    Method for two step authentication with Google Authenticator.
    it makes a POST to url_to_challenge_signin with the code generated on user's authenticator app.

    `code`: generated in user;s Google Authenticator app.
    `url_to_challenge_signin`: the url to post otp and other data to authenticate.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `utils.make_payload` function.
    '''

    error = None

    # add otp to payload
    payload['Pin'] = code

    try:
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    return resp_page, error, session


def two_step_login_with_text_msg(session, payload, url_to_challenge_signin, otp):
    '''
    Method for two step authentication using text message.

    `otp`: otp sent to user's mobile number.
    `url_to_challenge_signin`: the url to post otp and other data to.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `utils.make_payload` function.
    '''

    error = None

    # if the page was not what was expected (i.e. a page with a form having hidden input containing
    # data to send to POST request) then need to return error and log the page for debugging.
    try:
        # add otp to payload
        payload['Pin'] = otp

        # This specify action to send OTP in the POST request submitting email and password. Need
        # to remove from payload for POST otherwise we make the same request again and sends OTP
        # again.
        payload.pop('SendMethod')
    except:
        file_name = utils.log_error("second step login", payload)
        error = 500
        return None, error, session

    try:
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    return resp_page, error, session


def two_step_login_with_backup_code(session, payload, url_to_challenge_signin, code):
    '''
    Method for two step authentication with backup codes.

    `code`: backup code
    `url_to_challenge_signin`: the url to post otp and other data to.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `utils.make_payload` function.
    '''
    error = None

    # add otp to payload
    payload['Pin'] = code

    try:
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    return resp_page, error, session


def second_step_login(session, method, url, payload, query_params, otp):
    '''
    Calls appropriate functions based upon the two factor method.
    '''

    error = None

    # the url to make POST request to send otp to user
    url_to_challenge_signin = url.split('?')[0]

    # login with Google prompt
    if method == 1:
        response, error, session = two_step_login_with_prompt(session, payload, query_params,
                                                              url_to_challenge_signin)

        cookies = session.cookies

        # if login was not successful, appropriate cookies will not get set
        if not error and len(cookies) < 7:
            error = handle_prompt_error(response)

    # login with Google Authenticator
    elif method == 2:
        response, error, session = two_step_login_with_authenticator(session, payload,
                                                                     url_to_challenge_signin, otp)

        cookies = session.cookies

        # if login was not successful, appropriate cookies will not get set
        if not error and len(cookies) < 7:
            response, error, session = handle_otp_error(response, session)

    # login with text msg
    elif method == 3:
        response, error, session = two_step_login_with_text_msg(session, payload,
                                                                url_to_challenge_signin, otp)
        cookies = session.cookies

        # if login was not successful, appropriate cookies will not get set
        if not error and len(cookies) < 7:
            response, error, session = handle_otp_error(response, session)

    # login with backup code
    elif method == 4:
        response, error, session = two_step_login_with_backup_code(session, payload,
                                                                   url_to_challenge_signin, otp)

        cookies = session.cookies

        # if login was not successful, appropriate cookies will not get set
        if not error and len(cookies) < 7:
            response, error, session = handle_otp_error(response, session)

    # if input method didn't match
    else:
        error = 400
        return None, error, session

    return response, error, session
