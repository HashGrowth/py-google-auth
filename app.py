import falcon
import login

from wsgiref import simple_server


api = app = falcon.API()
api.add_route('/login', login.NormalLogin())
api.add_route('/step_two_login', login.StepTwoLogin())
api.add_route('/change_method', login.ChangeMethod())

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()
