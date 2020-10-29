import io
import re
import time
from contextlib import redirect_stdout

import discord

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandContext, CommandResult, EmbedType, DiscordPermissionHandler


@mrvn_module("BaseModule", "Модуль с основными функциями.")
class BaseModule(Module):
    async def on_enable(self):
        @mrvn_command(self, ["cmds", "help"], "Список команд, их аргументы и описание.", keys_desc=["--all"])
        class CmdsCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "", title="Список команд")

                count = 0

                for command in list(self.module.bot.command_handler.commands.values()):
                    if command.perm_handler.has_permission(ctx.message.author) or "all" in ctx.raw_keys:
                        count += 1

                        embed.add_field(
                            name=command.get_detailed_name(),
                            value=command.description, inline=False)

                embed.description = "Всего команд: %s" % count

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, ["modules", "mods"], "Список модулей, их описание.")
        class ModulesCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                embed: discord.Embed = ctx.get_embed(EmbedType.INFO,
                                                     "Всего модулей: %s" % len(self.module.bot.module_handler.modules),
                                                     title="Список модулей")

                for module in self.module.bot.module_handler.modules:
                    embed.add_field(name=module.name, value=module.description, inline=False)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, ["reload", "rd"], "Перезагрузить все модули бота.",
                      perm_handler=DiscordPermissionHandler(["administrator"]), should_await=False)
        class ReloadCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                self.module.bot.start_time = time.time()

                out = io.StringIO()
                with redirect_stdout(out):
                    self.module.logger.info("Начата перезагрузка модулей...")

                    for module in list(self.module.bot.module_handler.modules):
                        self.module.bot.module_handler.unload_module(module)
                        self.module.bot.command_handler.unregister_module_commands(module.name)

                    self.module.bot.module_handler.load_modules()

                    await self.module.bot.on_ready()

                await ctx.send_embed(EmbedType.INFO,
                                     "```prolog\n%s```" % re.compile(r'\x1b[^m]*m').sub("", out.getvalue()),
                                     "Лог перезагрузки")

                return CommandResult.ok()

        @mrvn_command(self, ["params", "pr"], "Просмотр и управление параметрами бота.",
                      args_desc="[set <ключ> <значение>]",
                      perm_handler=DiscordPermissionHandler(["administrator"]))
        class ParamsCommand(Command):
            @staticmethod
            def parse_value_for_type(value: str, value_type):
                if value_type == str:
                    return value
                elif value_type == bool:
                    if value.lower() in ("yes", "true", "yeah", "da", "yea", "+", "positive"):
                        return True
                    elif value.lower() in ("no", "false", "nah", "net", "nope", "-", "negative"):
                        return False
                    else:
                        return None
                elif value_type == int:
                    try:
                        return int(value)
                    except ValueError:
                        return None
                elif value_type == float:
                    try:
                        return float(value)
                    except ValueError:
                        return None
                else:
                    raise ValueError

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) > 0 and ctx.args[0].lower() == "set":
                    if len(ctx.args) < 3:
                        return CommandResult.args_error(
                            "Вы указали параметр `set`, но вы не указали ключ и/или значение.")

                    try:
                        param = self.module.bot.module_handler.params[ctx.args[1]]
                    except KeyError:
                        return CommandResult.error("Параметр не найден.")

                    try:
                        value_parsed = self.parse_value_for_type(" ".join(ctx.args[2:]), type(param))
                    except ValueError:
                        return CommandResult.error(
                            "Этот параметр невозможно изменить, так как его тип не позволяет получить значение из "
                            "текста.")

                    if value_parsed is None:
                        return CommandResult.error("Не удалось привести значение к типу. Проверьте правильность "
                                                   "значениия.")

                    self.module.bot.module_handler.set_param(ctx.args[1], value_parsed, True)

                    return CommandResult.ok()

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "Параметров загружено: %s" % len(
                    self.module.bot.module_handler.params), "Список параметров")

                for key, value in self.module.bot.module_handler.params.items():
                    embed.add_field(name="%s [тип: %s]" % (key, type(value).__name__),
                                    value=value if type(value) not in (dict, list) else "Значение не отображено",
                                    inline=False)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, ["die", "off"], "Выключить бота.", perm_handler=DiscordPermissionHandler(["administrator"]),
                      should_await=False)
        class DieCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                await ctx.message.channel.send(embed=ctx.get_embed(EmbedType.ERROR, "", "До связи."))

                await self.module.bot.close()

                return CommandResult.ok("")

        @mrvn_command(self, ["man", "info"], "Вывести помощь по конкретной команде", args_desc="<имя команды>")
        class HelpCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                command = self.module.bot.command_handler.find_command(ctx.args[0].lower())

                if not command:
                    return CommandResult.error("Команда с таким именем не найдена.")

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "", "Информация о команде")
                embed.add_field(name=command.get_detailed_name(), value=command.description)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()
