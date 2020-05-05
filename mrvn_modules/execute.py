import platform
import subprocess

from decorators import mrvn_module, mrvn_command
from modular import *


class MyGlobals(dict):
    # noinspection PyMissingConstructor
    def __init__(self, globs, locs):
        self.globals = globs
        self.locals = locs

    def __getitem__(self, name):
        try:
            return self.locals[name]
        except KeyError:
            return self.globals[name]

    def __setitem__(self, name, value):
        self.globals[name] = value

    def __delitem__(self, name):
        del self.globals[name]


premade_code = """
import io
import asyncio
from contextlib import redirect_stdout

async def execute():
    out = io.StringIO()
    is_error = False
    with redirect_stdout(out):
        try:
%s
        except Exception as e:
            is_error = True
            out.write(str(e))

    await ctx.send_embed(EmbedType.ERROR if is_error else EmbedType.OK, out.getvalue(),
                         "Код выполнен с ошибкой" if is_error else "Код выполнен успешно")
asyncio.ensure_future(execute())
"""


def _exec(code: str, g, l):
    d = MyGlobals(g, l)
    code_for_embed = ""

    for line in code.splitlines(keepends=True):
        code_for_embed = code_for_embed + "            " + line

    exec(premade_code % code_for_embed, d)


@mrvn_module("Execute", "Модуль, который позволяет выполнять код и консольные команды.")
class ExecuteModule(Module):
    user_list = [287157820233875458, 308653925379211264, 337762030138163200, 327420598588276736]

    async def on_enable(self):
        @mrvn_command(self, "execute", "Выполнить Python-код из сообщения", "<\\`\\`\\`Python код\\`\\`\\`",
                      perm_handler=UserWhitelistPermissionHandler(self.user_list))
        class ExecuteCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                code = ctx.message.content.split("```")[1].strip().rstrip()

                if len(code) < 3:
                    return CommandResult.args_error()

                self.module.logger.warn("Выполнение кода\n%s" % code)

                _exec(code, globals(), locals())

                return CommandResult.ok()

        @mrvn_command(self, "shell", "Выполнить консольную команду.", "<команда>",
                      perm_handler=UserWhitelistPermissionHandler(self.user_list))
        class ShellCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                command = " ".join(ctx.clean_args)

                if "shutdown" in command.lower() or "restart" in command.lower():
                    return CommandResult.error(
                        """
Использование этой команды - нарушение закона!. Закона жизни, который гласит:
Перед пацанами базар держи
Перед другом - слово.
Родителей и девушку люби, 
И храни веру перед Богом...
""")

                self.module.logger.warn("Выполнение консольной команды %s" % command)

                encoding = "cp866" if platform.system() == "Windows" else "utf-8"

                try:
                    result = subprocess.check_output(command, shell=True, timeout=5, stderr=subprocess.STDOUT)
                except subprocess.TimeoutExpired:
                    return CommandResult.ok("Превышено время ожидания получения ответа команды",
                                            "Консольная команда выполнена")
                except subprocess.CalledProcessError as sex:
                    return CommandResult.error(sex.output.decode(encoding), "Не удалось выполнить консольную команду")
                else:
                    return CommandResult.ok(result.decode(encoding), "Консольная команда выполнена")
