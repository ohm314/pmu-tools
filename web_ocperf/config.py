import yaml


CONFIG_FILE = './config.yaml'


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

config = AttrDict(yaml.load(file(CONFIG_FILE)))
