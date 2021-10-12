from json import JSONDecoder


class FastJsonDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

    def jsonToClass(self):
        raise NotImplementedError("jsonToClass() must be implemented on a subclass")

    def hook(self, obj):
        for keys, C in self.jsonToClass().items():
            if set(keys) == set(obj.keys()):
                args = []
                for key in list(keys):
                    args.append(obj[key])
                return C(*args)
        return obj
