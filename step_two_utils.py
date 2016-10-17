import json
import os
import requests


from . import utils

# directory path for storing log files in case of unhandled cases.
log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


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
        error = "Parsing Error"
        return None, error, session

    try:
        # make call to wait for user response
        reply_from_user = session.post(await_url % key, headers=headers,
                                       data=json.dumps({"txId": txId}))

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, error, session

    # convert response to json.
    reply_json = json.loads(reply_from_user.content.decode('utf-8'))

    # if request was not appropriate, log the response for further debugging.
    if 'error' in reply_json and reply_json['error']['code'] == 500:
        # log the error
        file_name = utils.log_error("second step login", reply_json)
        error = "Parsing Error"
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
        error = "Parsing Error"
        return reply_from_user, error, session

    try:
        # make final call to sign in
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
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
        error = "Connection Error"
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
        error = "Parsing Error"
        return None, error, session

    try:
        resp_page = session.post(url_to_challenge_signin, data=payload)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
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
        error = "Connection Error"
        return None, error, session

    return resp_page, error, session


def second_step_login(session, method, url, payload, query_params, otp):
    '''
    Calls appropriate funtions based upon the two factor method.
    '''

    error = None

    # the url to make POST request to send otp to user
    url_to_challenge_signin = url.split('?')[0]

    # login with Google prompt
    if method == 1:
        resp_page, error, session = two_step_login_with_prompt(session, payload, query_params,
                                                               url_to_challenge_signin)

        # if user does not respond for prompt
        if isinstance(resp_page, dict) and resp_page['error']['code'] == 500:
            return resp_page, "Time Out", session

    # login with Google Authenticator
    elif method == 2:
        resp_page, error, session = two_step_login_with_authenticator(session, payload,
                                                                      url_to_challenge_signin, otp)

    # login with text msg
    elif method == 3:
        resp_page, error, session = two_step_login_with_text_msg(session, payload,
                                                                 url_to_challenge_signin, otp)

    # login with backup code
    elif method == 4:
        resp_page, error, session = two_step_login_with_backup_code(session, payload,
                                                                    url_to_challenge_signin, otp)

    # if input method didn't match
    else:
        error = "Invalid Method"
        return None, error, session

    set_cookies = session.cookies

    # if login was not succesful, there might be some error
    if len(set_cookies) < 7:
        # log the page
        file_name = utils.log_error("second step login", resp_page.text)

        error = utils.scrap_error(resp_page.text)

        if error and "Wrong" in error:
            error = "Wrong Code"

        elif error and "Enter a code" in error:
            error = "Empty Code"

        # If user denies prompt login.
        elif resp_page and "you canceled it" in resp_page.text:
            error = "Prompt Denied"

        else:
            error = "Parsing Error"

    return resp_page, error, session
