import json
import os
import requests

import utils

log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


def two_step_login_with_prompt(session, payload, q_params, url_to_challenge_signin):
    '''
    Method for two step authentication with Google prompt.
    Collects a key and txId from the `form_html` to create a payload to send to next page,
    which awaits use confirmation from prompt.
    When User confirms, it makes a POST call to final challenge url to verify the request.
    If request was accepted, it returns the google play home page with user logged in.

    `url_to_challenge_signin`: the url to make final call to verify request status
    and allow/deny login.
    `await_url`: url to make a POST call to check if a user responded on prompt.
    `q_params`: These are two parameters, one a query parameter and the other a payload item;
    used to call `await_url`.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `utils.make_payload` function.
    '''
    error = None

    await_url = "https://content.googleapis.com/cryptauth/v1/authzen/awaittx?alt=json&key=%s"

    # headers are necessary to specify the referer and content type else request fails.
    headers = {"Referer": url_to_challenge_signin, "Content-Type": "application/json"}
    key = q_params['key']
    txId = q_params['txId']

    try:
        # make call to wait for user response
        reply_from_user = session.post(await_url % key, headers=headers,
                                       data=json.dumps({"txId": txId}))

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, error, session

    reply_json = json.loads(reply_from_user.content.decode('utf-8'))

    # if request was not appropriate
    if 'error' in reply_json and reply_json['error']['code'] == 500:
        # log the error
        f = open(log_dir + "request_to_await_url_log.html", 'w')
        f.write(str(reply_json))
        f.close()

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
        f = open(log_dir+"await_url_resp.html", 'w')
        f.write(reply_from_user.content.decode('utf-8'))
        f.close()

        error = "Parsing Error"
        return reply_json, error, session

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
    It makes a GET to the page where user's asked to enter the code.
    Collects data from the login page and
    post to next page with the code generated on user's authenticator app.

    `url_to_challenge_signin`: the url to post otp and other data to authenticate.
    `form_html`: It is the page which comes after submitting the password. This page contains
    payload fields for Google Authenticator method.
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
    Collects data from the login page and post to next page with the OTP received on user's device.

    `url_to_challenge_signin`: the url to post otp and other data to.
    `form_html`: It is the page which comes after submitting the password. This page contains
    payload fields for text msg method.
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
        f = open(log_dir+"text_msg_form_log.html", 'w')
        f.write(payload)
        f.close()

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
    Collects data from the login page and post to next page with the backup code received from user

    `url_to_challenge_signin`: the url to post otp and other data to.
    `form_html`: It is the page which comes after submitting the password. This page contains
    payload fields for backup code method.
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


def second_step_login(session, method, url, payload, q_params, otp):
    '''
    4. Calls appropriate funtions based upon the method selected from previous function.
    '''

    error = None

    methods = utils.get_method_names()

    # the url to make POST request to send otp to user
    url_to_challenge_signin = url.split('?')[0]

    # login with Google prompt
    if method == 1:
        resp_page, error, session = two_step_login_with_prompt(session, payload, q_params,
                                                               url_to_challenge_signin)

        # if user does not respond
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
        if resp_page and "Wrong code. Try again." in resp_page.text:
            error = "Wrong Code"

    if resp_page and "you canceled it" in resp_page.text:
        error = "Prompt Denied"

    return resp_page, error, session
