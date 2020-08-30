import random

from decorators import mrvn_module, command_listener, mrvn_command
from modular import Module, CommandListener, Command, CommandContext, EmbedType, CommandResult


class PendingCommand:
    ctx: CommandContext
    result: int
    command: Command

    def __init__(self, ctx, result, command):
        self.ctx = ctx
        self.result = result
        self.command = command


user_cmd_list = {}


@mrvn_module("Neo", "UNDEFINED")
class NeoModule(Module):
    async def on_enable(self):
        @mrvn_command(self, "mat", "Получить доступ к команде", "<ответ>")
        class MatCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if ctx.message.author.id not in user_cmd_list or user_cmd_list[ctx.message.author.id] is True:
                    return CommandResult.error("Вам еще не нужно отвечать.")

                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                try:
                    answer = int(ctx.args[0])
                except ValueError:
                    return CommandResult.args_error("Укажите число.")

                pending = user_cmd_list[ctx.message.author.id]

                if answer != pending.result:
                    return CommandResult.error("Вы указали неверный ответ!!!!")

                user_cmd_list[ctx.message.author.id] = True

                await self.module.bot.command_handler.handle(pending.ctx.message)

                return CommandResult.ok()

        @command_listener(self)
        class NeoCommandListener(CommandListener):
            async def on_command_pre_execute(self, command: Command, ctx: CommandContext) -> bool:
                if ctx.message.author.id == 337762030138163200:
                    return True
                if not bool(random.getrandbits(1)):
                    return True
                elif command.name == "mat":
                    return True
                elif ctx.message.author.id in user_cmd_list and user_cmd_list[ctx.message.author.id] is True:
                    return True

                sum_1 = random.randint(100, 500)
                sum_2 = random.randint(100, 500)
                action = bool(random.getrandbits(1))

                result = (sum_1 + sum_2) if action else (sum_1 - sum_2)

                await ctx.send_embed(EmbedType.ERROR,
                                     "Привет, друг! Прежде чем я позволю тебе выполнить эту команду, ты должен решить "
                                     "следующий пример!\n\n**%s**\n\nПосле этого, напиши !mat <результат> и твоя "
                                     "команда сразу будет выполнена!" % (
                                             "%s %s %s" % (sum_1, "+" if action else "-", sum_2)))

                user_cmd_list[ctx.message.author.id] = PendingCommand(ctx, result, command)

                return False
