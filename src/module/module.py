from command import CommandSpec

class Module:
    def __init__(self, cls: "ModuleBase", *, id, name, description="", authors=None):
        if authors is None:
            authors = []
        self.authors = authors
        self.description = description
        self.name = name
        self.id = id
        self.cls = cls
        for command in filter(lambda x: x is CommandSpec, self.cls.__dict__.values()):
            command.module = self
            pass

    def preinit(self):
        self.cls.preinit()


class ModuleBase:
    def preinit(self): # Загрузка ресурсов и другой хероты
        pass

    def init(self, bot): # Регистрация всякой хуеты
        pass
