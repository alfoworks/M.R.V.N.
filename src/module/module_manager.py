from command import CommandSpec


class ModuleManager:
    modules = []
    commands = []

    @classmethod
    def add_module(cls, module):
        cls.modules.append(module)

    @classmethod
    def preinit(cls):
        for module in cls.modules:
            pass

    @classmethod
    def add_command(cls, command: CommandSpec):
        cls.commands.append(command)
