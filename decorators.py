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


def mrvn_command(module: modular.Module, name: str, desc: str, args_desc: str = "", keys_desc=None,
                 perm_handler: modular.PermissionHandler = None, should_await: bool = True):
    if keys_desc is None:
        keys_desc = []

    if perm_handler is None:
        perm_handler = modular.AcceptAllPermissionHandler()

    def decorator(cls):
        module.bot.command_handler.register_command(
            cls(name, desc, args_desc, keys_desc, perm_handler, module, should_await))

        return cls

    return decorator
