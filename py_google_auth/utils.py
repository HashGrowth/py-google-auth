import jsonpickle
import logging
import os
import platform
import requests
import time

from bs4 import BeautifulSoup

# directory path for storing log files in case of unhandled cases.
try:
    log_dir = os.environ['PY_GOOGLE_AUTH_LOG_PATH']
except:
    system_user = os.environ['USER']
    dir_ = "/home/" + system_user + "/logs/py_google_auth"

    if not os.path.isdir(dir_):
        os.makedirs(dir_)

    log_dir = dir_ + "/"
    logging.warning("You have not set a path for error logging, using " + dir_)
else:
    if not log_dir.endswith("/"):
        log_dir = log_dir + "/"


def serialize_session(session):
    '''
    Takes a session object and serializes its attribute dictionary.
    '''

    session_dict = session.__dict__
    encoded = jsonpickle.encode(session_dict)
    return encoded


def deserialize_session(session):
    '''
    Takes a dictionary having a session object's atributes and deserializes it into a sessoin
    object.
    '''

    decoded = jsonpickle.decode(session)
    new_session = requests.session()
    new_session.__dict__.update(decoded)
    return new_session


def clean_session(session):
    '''
    We embedded some extra variables while sending session to network,
    These are not part of requests session, so we need to remove them.
    This method removes those extra attributes.
    '''

    attrs = ['next_url', 'q_params', 'select_method_url', 'prev_payload']
    for attr in attrs:
        if attr in session.__dict__:
            session.__delattr__(attr)

    return session


def make_payload(page):
    '''
    Function to get necesary data i.e. cookies and form hidden fields from a login form page
    to post with the POST request as payload for next step.

    Fields include:
        * ChallengeId: This specifies step no. in login.
        * ChallengeType: This specifies the type of tfa method by an integer.
        * Continue: URL to redirect after login.
        * TL: some query parameter.
        * gxf: some query parameter.
    These are common to all requests, others specific to a method are used in the method specific
    functions and are briefed there.
        '''
    payload = {}

    # collect all inputs from the form, these contains the parameters for payload.
    input_elements = BeautifulSoup(page).find('form').find_all('input')

    # create a payload dictionary
    for item in input_elements:
        if item.has_attr('value') and item.has_attr('name'):
            payload[item['name']] = item['value']

    return payload


def get_method_names():
    '''
    Returns google two factor authentication methods.
    '''

    methods = {1: ["Google prompt", "az"],
               2: ["Google Authenticator", "totp"],
               3: ["text message", "ipp"],
               4: ["backup code", "bc"]
               }

    return methods


def get_available_methods(page):
    '''
    It collects all the available mthods for two factor auth from the form for select method.
    '''

    available_methods = []
    error = None

    try:
        soup = BeautifulSoup(page)

        # the html elemnets containing method names
        method_spans = soup.find_all('span', class_="mSMaIe")

        for item in method_spans:
            available_methods.append(item.text)

    except:
        file_name, hostname = log_error("select alternate", page)
        error = 500
        response = {'file_name': file_name, 'hostname': hostname}

    else:
        response = {'available_methods': available_methods}

    return response, error


def get_query_params(page):
    '''
    These parameters are required in Google Prompt method.
    So prepare them before sending response.
    '''

    # get the key and id to make call to `await_url`
    soup = BeautifulSoup(page)
    div_with_key_id = soup.find('div', class_='LJtPoc')

    try:
        # this is a query parameter sent with `await_url` in `step_two_utils.login_with_prompt`
        # method.
        key = div_with_key_id.get('data-api-key')

        # a payload item sent in POST request to `await_url`.
        txId = div_with_key_id.get('data-tx-id')

        data = {'key': key, 'txId': txId}

    except:
        # log exception
        file_name, hostname = log_error("second step login", page)
        data = {}

    return data


def get_phone_number(page):
    '''
    Function to extract phone number to which otp is sent, from the response page.
    '''
    soup = BeautifulSoup(page)
    number_container = soup.find(class_="DZNRQe")
    number = number_container.text

    return number


def scrap_error(page):
    '''
    This function scraps an error message (if exist) from a response page.
    '''
    soup = BeautifulSoup(page)
    error_span = soup.find('span', id='errorMsg')

    if error_span:
        error = error_span.text
    else:
        error = None

    return error


def log_error(step, content):
    '''
    This function logs a page for error.
    It is called whenever an unhandled exception will occur.
    `step`: The step in login process, it could be normal_login, step_two_login or
    select_alternate.
            It makes it easy to identify the file in logs.
    `content`: content to log.
    '''
    file_name = step + "- " + time.strftime("%d-%m-%Y %H-%M-%S") + ".html"
    f = open(log_dir+file_name, 'w')
    f.write(content)
    f.close()

    # hostname of the machine where the py-google-auth is running
    hostname = platform.node()

    return file_name, hostname


def handle_default_method(default_method, response, session):
    '''
    This function is used when the default method is not available.
    '''
    response_data = {}

    # create payload from response text
    payload = make_payload(response.text)

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
        query_params = get_query_params(response.text)
        session.query_params = query_params

    # if default method is text message, get the phone number to which otp was sent.
    if default_method == 3:
        phone_num = get_phone_number(response.text)
        response_data['number'] = phone_num

    response_data['default_method'] = default_method

    return response_data, session
