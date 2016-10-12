import os
import requests

from bs4 import BeautifulSoup

from . import utils

# directory path for storing log files in case of unhandled cases.
log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


def get_payload_for_select_page(form_html, form_key):
    '''
    Function to collect payload from method selection page.
    The page contains multiple forms with hidden fields having payload params.
    using `form_key` we select appropriate form and then collect input field values.
    You can read payload field details in `utils.make_payload` function.
    '''

    payload = {}

    # find all the forms
    forms = BeautifulSoup(form_html).find_all('form')

    # collect all inputs from the appropriate form, these contains the parameters for payload.
    inputs = forms[form_key].find_all('input')

    # create a payload dictionary
    for item in inputs:
        if item.has_attr('value') and item.has_attr('name'):
            payload[item['name']] = item['value']

    return payload


def get_method_for_selection(selected_method):
    '''
    Returns method code for a complete method string given by google while selecting
    alternate tfa method.
    '''
    methods = utils.get_method_names()
    method = [method for method in methods if methods[method][0] in selected_method][0]
    return method


def get_alternate_method(session, method, select_challenge_url):
    '''
    Function to get the url for alternatively selected method from the form in try another
    method page.
    '''

    error = None

    # url to form next challenge GET request url according to user choice
    url_to_challenge_signin = "https://accounts.google.com/signin/challenge/"

    # all two factor methods with protocols they use
    methods = utils.get_method_names()

    # make a GET call to collect payload
    try:
        form_html = session.get(select_challenge_url)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, error, session

    # available methods on a user's account
    available_methods, error = utils.get_available_methods(form_html.text)

    if not error:
        try:
            # map protocol and selection according to selected method using the methods dictionary
            selection = available_methods.index(method)
            protocol = [methods[item][1] for item in methods if methods[item][0] in method][0]
        except:
            error = "Invalid Method"
            return form_html, error, session

    else:
        return form_html, error, session

    # prepare payload from get_payload_for_select_page
    # the methods is seperated because method selection page contains multiple forms
    # one form for each method, and each form has some different payload params
    # depending upon the method, so a different logic required
    payload = get_payload_for_select_page(form_html.text, selection)

    # if the page was not what was expected (i.e. a page with a form having hidden input containing
    # challengeId to send to POST request) then need to return error and log the page for debugging
    try:
        challengeId = payload['challengeId']

    except:
        f = open(log_dir+"select_method_form_log.html", 'w')
        f.write(form_html.text)
        f.close()

        error = "Parsing Error"
        return form_html, error, session

    # join the base url, protocol and challengeId to form the POST url
    next_challenge_post_url = url_to_challenge_signin + protocol + "/" + challengeId

    try:
        # make a POST call that will send otp (for Authenticator and text msg), or prompt for
        # Google prompt and return appropriate form.
        challenge_resp = session.post(next_challenge_post_url, data=payload)

    except(requests.exceptions.ConnectionError):
        error = "Connection Error"
        return None, error, session

    return challenge_resp, error, session
