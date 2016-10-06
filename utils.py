import os
import jsonpickle
import requests

from bs4 import BeautifulSoup

log_dir = os.environ.get('PY_GOOGLE_AUTH_LOG_PATH')


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
    soup_login = BeautifulSoup(page).find('form').find_all('input')

    # create a payload dictionary
    for u in soup_login:
        if u.has_attr('value') and u.has_attr('name'):
            payload[u['name']] = u['value']

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


def get_query_params(page):
    '''
    These parameters are required in Google Prompt method.
    So prepare them before sending response.
    '''

    # get the key and id to make call to `await_url`
    soup = BeautifulSoup(page)
    div_with_key_id = soup.find('div', class_='LJtPoc')
    key = div_with_key_id.get('data-api-key')
    txId = div_with_key_id.get('data-tx-id')

    return {'key': key, 'txId': txId}
