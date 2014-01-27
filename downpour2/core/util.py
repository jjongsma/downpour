from storm.info import get_cls_info
import json


class ObjectEncoder(json.JSONEncoder):

    def default(self, o):
        return o.__dict__


class StormModelEncoder(json.JSONEncoder):

    def default(self, o):

        if not hasattr(o, "__storm_table__"):
            raise TypeError(repr(o) + " is not JSON serializable")

        result = {}

        cls_info = get_cls_info(o.__class__)
        for name in cls_info.attributes.iterkeys():
            result[name] = getattr(o, name)

        return result