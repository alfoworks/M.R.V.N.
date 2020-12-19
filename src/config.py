import json
import os
from threading import Lock
from typing import Union

config_file = "config.json"

def field(path: str, default_value: Union[int, str, float, list] = None):
    return ConfigurationEntry(path, default_value)

#region Служебная хрень
def load_config():
    if os.path.exists(config_file):
        with open(config_file) as f:
            return json.load(f)
    else:
        return {}

class ConfigurationEntry:
    def __init__(self, path, default_value):
        self.path = path
        self.default_value = default_value

    def __get__(self, instance, owner: "Config"):
        config = owner.config
        try:  # Ищем в ОЗУ ключ
            cache = config
            for entry in self.path.split("."):
                cache = cache[entry]
            return cache
        except KeyError:  # Не нашли, создаем и сохраняем
            if self.default_value is None:
                return None
            cache = config
            path = self.path.split(".")
            for entry in path[:-1]:
                cache[entry] = dict()
                cache = cache[entry]
            cache[path[-1]] = self.default_value
            owner.save()
            return self.default_value

    def __set__(self, instance: "Config", value):
        config = instance.config
        cache = config
        path = self.path.split(".")
        for entry in path[:-1]:
            if entry not in cache:
                cache[entry] = {}
            cache = cache[entry]
        cache[path[-1]] = value
        instance.save()


class ConfigurationMeta(type): # Класс позволяет __set__ работать без инициализации класса
    def __setattr__(self, key, value):
        obj = self.__dict__.get(key, None)
        if type(obj) is ConfigurationEntry:
            return obj.__set__(self, value)
        return super().__setattr__(key, value)
#endregion

class Config(metaclass=ConfigurationMeta):
    config = load_config()
    _lock = Lock()

    def __init__(self):
        raise RuntimeError("Static class initialization")

    @classmethod
    def save(cls): # TODO может быть необходим asyncio
        cls._lock.acquire() # Это не означает, что эта строка не нужна
        with open(config_file, "w") as f:
            json.dump(cls.config, f, indent=2)
        cls._lock.release()

    prefix = field("discord.prefix", "/")
    modules_dir = field("modules_dir", "modules")