import os
import re
import requests

from bs4 import BeautifulSoup

from . import utils

# directory path for storing log files in case of unhandled cases.
log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


def is_valid_email(email):
    '''
    Validates an email based on its pattern.
    '''

    valid_pattern = '[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}'
    found = re.search(valid_pattern, email, re.I)

    try:
        found.group()
        return True
    except AttributeError:
        return False


def check_response(page):
    '''
    Checks whether the response is correct to proceed or not.
    '''
    soup = BeautifulSoup(page)
    challenge_picker = soup.find('ol', id='challengePickerList')

    if challenge_picker:
        return None
    else:
        error = 500
        return error


def select_alternate_method(session, current_form_page_url):
    '''
    Find the list of enabled methods on a google account for TFA.
    `session`: requests.Session object for the sequence of requests.
    `current_form_page_url`: url of the page which came as a response to the POST call in which,
    username and password were submitted.
    '''

    error = None

    # url to make a POST request to get the available methods page
    skip_url = "https://accounts.google.com/signin/challenge/skip"

    try:
        # current form will give necessary data to send as payload to skip_url
        form_html = session.get(current_form_page_url)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    payload = utils.make_payload(form_html.text)

    # if the page did not have the form it won't have payload, that shows the response page has
    # changed or the request was not appropriate.
    if not payload:
        file_name, hostname = utils.log_error("select alternate", form_html.text)
        error = 500
        response = {'file_name': file_name, 'hostname': hostname}
        return response, error, session

    try:
        # this will return the select challenge url and necessary parameters
        select_method_page = session.post(skip_url, data=payload)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    try:
        # get the page where all enabled method are listed for selection
        login_html = session.get(select_method_page.url)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    # check whether page contains list of methods
    error = check_response(login_html.text)

    if error:
        file_name, hostname = utils.log_error("select alternate", login_html.text)
        response = {'file_name': file_name, 'hostname': hostname}
        return response, error, session

    # find all the available methods from the response page.
    response, error = utils.get_available_methods(login_html.text)
    available_methods = response['available_methods']

    response = {'methods': available_methods, 'select_method_url': select_method_page.url}

    return response, error, session


def get_default_method(resp_page):
    '''
    Find the default method for two factor authentication from response text.
    `resp_page`: the page from which default method is extracted.
    '''

    error = None

    # get all the two factor method names.
    methods = utils.get_method_names()

    # if there was some problem with the default method, we need to ask user to use alternate
    if "Please try again later" in resp_page or "Something went wrong" in resp_page:
        # this is code is although used when an unexpected response occur, but in this case we need
        # this for step_two_login when this method is called from there we don't want response 503
        # hence using this (since now only codes are used for errors).
        error = 500

    # select method based on the text from response page.

    if "prompt to sign in" in resp_page:
        method = 1
        response = {'method': method}

    else:
        try:
            # elect method index according to its found text in the response page, for example if
            # 'text message' is found in the response text then default method is 'text message
            # otp' so its code will be returned.
            method = [m for m in methods if methods[m][0] in resp_page][0]

        except:
            file_name, hostname = utils.log_error("second step login", resp_page)
            error = 500
            response = {'file_name': file_name, 'hostname': hostname}
        else:
            response = {'method': method}

    return response, error


def normal_login(session, username, password, continue_url):
    '''
    Method for login to a normal account without TFA.
    `continue_url`: the url to call after login.
    '''

    # TODO: remove hard coded service name
    # url to the login form page.
    base_url_login = "https://accounts.google.com/ServiceLogin?"
    url_login = base_url_login + "service=androiddeveloper"

    # url to post login credentials and other data.
    url_auth = "https://accounts.google.com/ServiceLoginAuth?service=androiddeveloper"

    error = None

    try:
        form_html = session.get(url_login)

    except(requests.exceptions.ConnectionError):
        error = 504
        return None, error, session

    # payload to send with POST request, i.e. cookies, tokens etc. more details in
    # `utils.make_payload` function.
    payload = utils.make_payload(form_html.text)

    # if the page did not have the form it won't have payload, that shows the response page has
    # changed or the request was not appropriate.
    if not payload:
        file_name, hostname = utils.log_error("normal login", form_html.text)
        error = 500
        response = {'file_name': file_name, 'hostname': hostname}
        return response, error, session

    # add email, password and target url in payload
    payload['Email'] = username
    payload['Passwd'] = password
    payload['continue'] = continue_url

    try:
        response = session.post(url_auth, data=payload)

    except(requests.exceptions.ConnectionError):
        response = None
        error = 504

    set_cookies = session.cookies

    if len(set_cookies) < 7:

        if ("Google doesn't recognize that email" in response.text or
           "Wrong password" in response.text):
            error = 401
            return response, error, session

        # TODO: use some more specific text to identify captcha.
        # if captcha occured
        if "captcha" in response.text:
            error = 429
            return response, error, session

        # if TFA was enabled
        if "signin/challenge" in response.url:
            error = 303
            return response, error, session

        else:
            file_name, hostname = utils.log_error("normal login", response.text)
            error = 500
            response = {'file_name': file_name, 'hostname': hostname}

    return response, error, session


def login(username, password):
    '''
    Function to log into user's google account.
    '''
    # prepare requests session object. It will be used in all the consequent requests.
    session = requests.session()

    # TODO: Don;t hard code, see https://github.com/HashGrowth/py-google-auth/issues/2 for details.
    # url to finally redirect to.
    play_console_base_url = "https://play.google.com/apps/publish"

    # login normally
    response, error, session = normal_login(session, username, password, play_console_base_url)

    return response, error, session
