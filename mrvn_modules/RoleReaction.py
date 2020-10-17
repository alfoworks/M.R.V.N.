import json
import os
import re

from discord import *
from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext

regex = re.compile(r"<@&(\d+)>", re.MULTILINE)
CACHE_FILE = "rolereaction_cache.json"
EMOJI_START = 0x1F1E6
cache = {}


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


@mrvn_module("RoleReaction", "RoleReaction  - автоматическая система установки ролей")
class TestModule(Module):

    async def on_enable(self):
        global cache
        self.logger.info("Модуль запущен!")
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cache = json.load(f)
        # Можно убрать в принципе, если забитый диск не мешает
        for entry in cache:
            entry: str
            guild_id, channel_id, message_id = tuple(map(lambda x: int(x), entry.split("_")))
            guild: Guild = self.bot.get_guild(guild_id)
            if guild is None:
                del cache[entry]
                save_cache()
                continue
            channel: TextChannel = guild.get_channel(channel_id)
            if channel is None:
                del cache[entry]
                save_cache()
                continue
            try:
                await channel.fetch_message(message_id)
            except NotFound:
                del cache[entry]
                save_cache()
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
                    text += "%s - %s\n" % (chr(EMOJI_START + i), role.mention) # Сразу обьясняю что это за ад: это regional indicators в chr
                text += "\n\nНажмите на реакцию внизу, что бы выбрать роль. Уберите свою реакцию, что бы убрать роль."
                # Рисуем эмбед
                # Здесь нельзя использовать CommandResult, поскольку после отправки сообщения нужно получить айди и выполнить другие действия
                embed = Embed()
                embed.title = "RoleMention" # TODO ревью данной части кода и возможно рерайт, что бы подходило по стилю
                embed.description = text
                del text
                # Отправляем
                msg: Message = await ctx.message.channel.send(embed=embed)
                # Рисуем реакции
                for i in range(len(roles)):
                    await msg.add_reaction(chr(EMOJI_START + i))
                # Сохраняем данные
                cache["%s_%s_%s" % (msg.guild.id, msg.channel.id, msg.id)] = list(map(lambda x: x.id, roles))
                save_cache()
                return CommandResult.ok()

    async def on_event(self, event_name, *args, **kwargs):
        if event_name == "on_raw_reaction_add" or event_name == "on_raw_reaction_remove":
            payload: RawReactionActionEvent = args[0]
        else:
            return
        # Проверка на сообщение на сервере
        if payload.guild_id is None:
            return
        key = "%s_%s_%s" % (payload.guild_id, payload.channel_id, payload.message_id)
        # Проверка на то, что это искомое сообщение, на которое нужно ставить роли
        if key not in cache:
            return
        # Получение юзера
        guild: Guild = self.bot.get_guild(payload.guild_id)
        member: Member = guild.get_member(payload.user_id)
        # Проверка, что роль не кастомная
        if payload.emoji.id is not None:
            return
        roles = cache[key]
        index = ord(payload.emoji.name) - EMOJI_START
        # Проверка на индекс
        if index not in range(len(roles)):
            return
        # Получение роли
        role = guild.get_role(roles[index])
        # Установка
        if payload.event_type == "REACTION_ADD":
            await member.add_roles(role, reason="RoleReaction automatic system")
        elif payload.event_type == "REACTION_REMOVE":
            await member.remove_roles(role, reason="RoleReaction automatic system")


