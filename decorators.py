#  The MIT License (MIT)
#
#  Copyright © «2020» «ALFO:WorkS, Iterator»
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
