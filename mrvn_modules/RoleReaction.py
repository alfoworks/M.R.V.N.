import json
import re
from typing import Union

from discord import *
from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext, ModuleHandler

regex = re.compile(r"<@&(\d+)>", re.MULTILINE)
CACHE_FILE = "rolereaction_cache.json"
ADD = "add"
REMOVE = "remove"
EMOJI_START = 0x1F1E6
cache = {}


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


@mrvn_module("TestModule", "Тестовый модуль")
class TestModule(Module):

    async def on_enable(self):
        self.logger.info("Модуль запущен!")
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        # noinspection PyUnusedLocal
        @mrvn_command(self, "rolereaction", "Создать сообщение, добавление реакции на которое выдаст роль", args_desc="<roles...>")
        class TestCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                roles = []
                guild: Guild = ctx.message.guild
                # Находим регексом роли
                for match in regex.finditer(ctx.message.content):
                    roles.append(guild.get_role(
                        int(match.group(1))
                    ))
                # Проверяем количество
                if not roles:
                    return CommandResult.error("Вы не указали роли.")
                elif len(roles) > 20:
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
                    await msg.add_reaction(chr(EMOJI_START + i))
                # Сохраняем данные
                cache[msg.id] = list(map(lambda x: x.id, roles))
                save_cache()
                return CommandResult.ok()

    async def on_event(self, event_name, *args, **kwargs):
        if event_name == "on_reaction_add":
            reaction: Reaction = args[0]
            user: Union[Member, User] = args[1]
            action = ADD
        elif event_name == "on_reaction_remove":
            reaction: Reaction = args[0]
            user: Union[Member, User] = args[1]
            action = REMOVE
        else:
            return
        message: Message = reaction.message
        if reaction.custom_emoji:
            return
        if message.guild is None:
            return
        if str(message.id) not in cache:
            return
        roles = cache[message.id]
        index = ord(reaction.emoji) - EMOJI_START
        if index not in range(20):
            await message.remove_reaction(reaction.emoji, user)
            return
        if action == ADD:
            await user.add_roles(roles[index], reason="RoleReaction automatic system")
        elif action == REMOVE:
            await user.remove_roles(roles[index], reason="RoleReaction automatic system")


