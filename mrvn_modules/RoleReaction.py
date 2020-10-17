import json
import re

from discord import *
from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext, ModuleHandler

regex = re.compile(r"<@&(\d+)>", re.MULTILINE)
CACHE_FILE = "rolereaction_cache.json"
cache = {}


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


@mrvn_module("TestModule", "Тестовый модуль")
class TestModule(Module):

    async def on_enable(self):
        self.logger.info("Модуль запущен!")

        # noinspection PyUnusedLocal
        @mrvn_command(self, "rolereaction", "Создать сообщение, добавление реакции на которое выдаст роль", args_desc="<roles...>")
        class TestCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                roles = []
                # Находим регексом роли
                for match in regex.finditer(ctx.message.content):
                    guild: Guild = ctx.message.guild
                    roles.append(guild.get_role(
                        int(match.group(1))
                    ))
                # Проверяем количество
                if not roles:
                    return CommandResult.error("Вы не указали роли.")
                elif len(roles) > 26:
                    return CommandResult.error("Слишком много ролей.")
                # Рисуем сообщение
                text = "Выберите реакцию в соответствии с ролью, которую хотите получить:\n\n"
                for i, role in enumerate(roles):
                    role: Role
                    text += "%s - %s\n" % (chr(0x1F1E6 + i), role.mention) # Сразу обьясняю что это за ад: это regional indicators в chr
                text += "\n\nНажмите на реакцию внизу, что бы выбрать роль. Уберите свою реакцию, что бы убрать роль."
                # Рисуем эмбед
                # Здесь нельзя использовать CommandResult, поскольку после отправки сообщения нужно получить айди и выполнить другие действия
                embed = Embed()
                embed.title = "RoleMention" # TODO ревью данной части кода и возможно рерайт, что бы подходило по стилю
                embed.description = text
                del text
                # Отправляем
                msg: Message = ctx.message.channel.send(embed=embed)
                # Рисуем реакции
                for i in range(len(roles)):
                    await msg.add_reaction(chr(0x1F1E6 + i))
                # Сохраняем данные
                cache[msg.id] = list(map(lambda x: x.id, roles))
                save_cache()
                return CommandResult.ok()