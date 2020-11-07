from typing import List

import modular


def mrvn_module(name: str, desc: str):
    def decorator(cls):
        cls_init = cls.__init__

        def __init__(self, *args, **kwargs):
            self.name = name
            self.description = desc
            self.logger = modular.Logger(name)

            cls_init(self, *args, **kwargs)

        cls.__init__ = __init__

        return cls

    return decorator


def mrvn_command(module: modular.Module, aliases: List[str], desc: str, args_desc: str = "", keys_desc=None,
                 perm_handler: modular.PermissionHandler = None, should_await: bool = True,
                 special_handler: modular.CommandHandler = None):
    if keys_desc is None:
        keys_desc = []

    if perm_handler is None:
        perm_handler = modular.AcceptAllPermissionHandler()

    def decorator(cls):
        handler: modular.CommandHandler = module.bot.command_handler if special_handler is None else special_handler

        handler.register_command(
            cls(aliases, desc, args_desc, keys_desc, perm_handler, module, should_await))

        return cls

    return decorator


def command_listener(module: modular.Module, special_handler: modular.CommandHandler = None):
    def decorator(cls):
        handler: modular.CommandHandler = module.bot.command_handler if special_handler is None else special_handler

        listener = cls(module)

        handler.register_listener(listener)

        return cls

    return decorator
