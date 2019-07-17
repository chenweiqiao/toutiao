from functools import wraps

from flask import json
from werkzeug.wrappers import Response

from corelib.flask import Flask


def marshal(data, schema):
    """ 返回符合schma定义的字典 """
    if isinstance(data, (list, tuple)):
        return list(filter(None, [marshal(d, schema) for d in data]))

    result, errors = schema.dump(data)  # data为模型实例或者字典
    if errors:
        for item in errors.items():
            print('{}: {}'.format(*item))
    return result


class marshal_with(object):

    def __init__(self, schema_cls):
        self.schema = schema_cls()

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            resp = f(*args, **kwargs)
            return marshal(resp, self.schema)
        return wrapper


class ApiResult(object):

    def __init__(self, value, status=200):
        self.value = value
        self.status = status

    def to_response(self):
        if 'r' not in self.value:
            self.value['r'] = 0
        return Response(json.dumps(self.value), mimetype='application/json',
                        status=200 if self.status > 204 else self.status)


class ApiFlask(Flask):

    def make_response(self, rv):
        if isinstance(rv, Response):
            return rv

        status = 200

        if not isinstance(rv, (ApiResult, dict, Exception)) and \
           isinstance(rv, (tuple, list)) and \
           len(rv) == 2 and isinstance(rv[1], int):
            rv, status = rv
        if isinstance(rv, (dict, list)):
            dt = {'data': rv}
            rv = ApiResult(dt, status=status)
        if isinstance(rv, ApiResult):
            return rv.to_response()
        return Flask.make_response(self, rv)
