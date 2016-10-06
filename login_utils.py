import os
import requests

from bs4 import BeautifulSoup

import utils

log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


def select_alternate_method(session, current_form_page_url):
    '''
    5. Find the list of available methods on a google account for TFA.
    '''

    error = None

    # url to make a POST request to get the available methods page
    skip_url = "https://accounts.google.com/signin/challenge/skip"

    try:
        # current form will give necessary data to send as payload to skip_url
        form_html = session.get(current_form_page_url)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, None, error, session

    payload = utils.make_payload(form_html.text)

    try:
        # this will return the select challenge url and necessary parameters
        select_method_page = session.post(skip_url, data=payload)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, None, error, session

    # if POST was not successful, assume request was in appropriate and log request payload origin
    # page
    if select_method_page.status_code != 200:
        f = open(log_dir+"skip_url_response_log.html", 'w')
        f.write(form_html.text)
        f.close()

        error = "Parsing Error"
        return None, None, error, session

    try:
        # get all available methods
        login_html = session.get(select_method_page.url)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, None, error, session

    try:
        soup = BeautifulSoup(login_html.text)

        # the html elemnets containing method names
        method_spans = soup.find_all('span', class_="mSMaIe")

        available_methods = []
        for item in method_spans:
            available_methods.append(item.text)

    except:
        f = open(log_dir+"select_method_form_log.html", 'w')
        f.write(login_html.text)
        f.close()

        error = "Parsing Error"
        return None, None, error, session

    return available_methods, select_method_page.url, error, session


def get_default_method(resp_page):
    '''
    3. Find the default method for two factor authentication from response text.
    '''

    error = None
    methods = utils.get_method_names()

    # if there was some problem with the default method, we need to ask user to use alternate
    if "Please try again later" in resp_page or "Something went wrong" in resp_page:
        error = "Default not available"

    # select method based on the text from response page.

    if "prompt to sign in" in resp_page:
        method = methods[2][0]

    else:
        try:
            method = [m for m in methods if methods[m][0] in resp_page][0]

        except:
            f = open(log_dir+"default_method_form_log.html", 'w')
            f.write(resp_page)
            f.close()

            method = None
            error = "Parsing Error"

    return method, error


def normal_login(session, username, password, continue_url):
    '''
    2. Method for login to a normal account without TFA.

    `url_login`: url to the login form page.
    `url_auth`: url to post login credentials and other data.
    `payload`: payload to send with POST request, i.e. cookies, tokens etc. more details in
    `get_payload` function.
    These are extracted from GET request.
    '''

    url_login = "https://accounts.google.com/ServiceLogin?service=androiddeveloper"
    url_auth = "https://accounts.google.com/ServiceLoginAuth?service=androiddeveloper"
    error = None

    try:
        form_html = session.get(url_login)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, error, session

    # prepare payload to send with POST request
    payload = utils.make_payload(form_html.text)

    # add email, password and target url in payload
    payload['Email'] = username
    payload['Passwd'] = password
    payload['continue'] = continue_url

    try:
        resp_page = session.post(url_auth, data=payload)

    except(requests.exceptions.ConnectionError):
        resp_page = None
        error = "Connection error"

    if resp_page.status_code != 200:
        f = open(log_dir+"login_form_log.html", 'w')
        f.write(resp_page.text)
        f.close()

        error = "Parsing Error"
        return resp_page, error, session

    if ("Google doesn't recognize that email" in resp_page.text or
       "Wrong password" in resp_page.text):
        error = "Invalid credentials"
        return resp_page, error, session

    # TODO: use some more specific text to identify captcha.
    # if captcha occured
    if "captcha" in resp_page.text:
        error = "captcha"
        return resp_page, error, session

    # if TFA was enabled
    if "signin/challenge" in resp_page.url:
        error = "TFA"
        return resp_page, error, session

    return resp_page, error, session


def login(username, password):
    '''
    1. Function to log into user's google account.
    '''
    session = requests.session()

    # url to finally redirect to.
    play_console_base_url = "https://play.google.com/apps/publish"

    # login normally
    resp_page, error, session = normal_login(session, username, password, play_console_base_url)

    return resp_page, error, session
