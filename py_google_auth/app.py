import falcon

from wsgiref import simple_server

from . import login


# create API
api = app = falcon.API()

# create endpoints for API.
api.add_route('/login', login.NormalLogin())
api.add_route('/step_two_login', login.StepTwoLogin())
api.add_route('/change_method', login.ChangeMethod())
api.add_route('/resend_code', login.ResendCode())

# This block is required if running the file using `python app.py` to run the server.
# else if running using gunicorn; can ignore this block.
if __name__ == '__main__':
    httpd = simple_server.make_server('localhost', 8001, app)
    httpd.serve_forever()
