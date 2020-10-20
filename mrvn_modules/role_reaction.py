import json
import os

import discord

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext, DiscordPermissionHandler

CACHE_FILE = "rolereaction_cache.json"
ROLES = "roles"
CHANNEL_ID = "channel_id"
MESSAGE_ID = "message_id"
EMOJI_START = 0x1F1E6
UNDEFINED_ROLE = (-1, "Один из входов в дом Вампуса")

cache = {}


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


@mrvn_module("RoleReaction", "Автоматическая система установки ролей")
class RoleReactionModule(Module):

    async def on_enable(self):
        global cache

        self.logger.info("Модуль запущен!")

        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cache = json.load(f)

        @mrvn_command(self, name="rrm",
                      desc="Управляйте сообщением, с помощью которого пользователи могут получать роли",
                      args_desc="[create <канал>]/[remove <роли...>]/[add/rename <роль> [описание]]",
                      perm_handler=DiscordPermissionHandler(["administrator"]))
        class RoleReactionManagerCommand(Command):
            @staticmethod
            def create_embed(ctx) -> discord.Embed:
                text = "Выберите реакцию в соответствии с ролью, которую хотите получить:\n\n"
                dossier = cache[str(ctx.message.guild.id)]

                # Если роли есть
                if dossier[ROLES]:
                    for i, role_obj in enumerate(dossier[ROLES]):
                        role: discord.Role = ctx.message.guild.get_role(role_obj[0])

                        # Сразу обьясняю что это за ад: это regional indicators в chr
                        if role:
                            text += "%s - %s" % (chr(EMOJI_START + i), role.mention)

                            if role_obj[1]:
                                text += "- %s" % role_obj[1]

                            text += "\n"
                        else:
                            text += "%s - %s\n" % (chr(EMOJI_START + i), role_obj[1])

                    text += "\n\nНажмите на реакцию внизу, что бы получить роль. " \
                            "Уберите свою реакцию, что бы убрать роль."
                else:  # А если нет, то показываем вампуса. Без пикчи, там хуйня со цветом.
                    text += "Пока здесь нет ролей, что бы вы их выбрали. Зато здесь сидит Вампус."

                # Рисуем эмбед
                return ctx.get_custom_embed(text, "Выбор ролей", 0x3498DB, False)

            async def execute(self, ctx: CommandContext) -> CommandResult:
                # Проверки на аргументы
                if len(ctx.args) == 0:
                    return CommandResult.args_error()

                if ctx.args[0] not in ("create", "add", "remove", "rename"):
                    return CommandResult.args_error()

                # Смотрим че хочет юзер
                if ctx.args[0] == "create":
                    # Не заменять на try-except
                    # Почему? Юзеры скорее всего не будут указывать опциональный канал, а обработка исключения накладна
                    channel = ctx.message.channel_mentions and ctx.message.channel_mentions[0] or ctx.message.channel

                    # Создается структура сервера
                    cache[str(ctx.message.guild.id)] = {
                        CHANNEL_ID: channel.id,
                        MESSAGE_ID: 0,
                        ROLES: []
                    }

                    embed = self.create_embed(ctx)
                    msg: discord.Message = await channel.send(embed=embed)

                    cache[str(ctx.message.guild.id)][MESSAGE_ID] = msg.id
                    save_cache()
                if ctx.args[0] in ("add", "remove", "rename"):
                    # Проверки
                    try:
                        dossier = cache[str(ctx.message.guild.id)]
                    except KeyError:
                        return CommandResult.error("Вам необходимо создать сообщение заново.")

                    if not ctx.message.role_mentions:
                        return CommandResult.args_error()

                    if ctx.args[0] == "remove":
                        # Удаляются ВСЕ упомянутые роли с сообщения
                        for role in ctx.message.role_mentions:
                            role: discord.Role

                            for i, role_object in enumerate(dossier[ROLES]):
                                another_role_id, description = role_object

                                # Поиск необходимой роли для удаления
                                if another_role_id == role.id:
                                    # Замена на UNDEFINED
                                    dossier[ROLES][i] = UNDEFINED_ROLE

                        while dossier[ROLES] and dossier[ROLES][-1][0] == -1:
                            del dossier[ROLES][-1]
                    elif ctx.args[0] == "add":
                        if next(filter(lambda x: x[0] == ctx.message.role_mentions[0].id, dossier[ROLES]), None):
                            return CommandResult.error("Такая роль уже существует!")

                        added = False

                        # Находим свободное место
                        for i, role_object in enumerate(dossier[ROLES]):
                            if role_object[0] == -1:
                                # Выставляем роль и описание
                                dossier[ROLES][i] = (ctx.message.role_mentions[0].id, " ".join(ctx.args[2:]))

                                added = True
                                break

                        if not added:
                            # Тут tuple. лишних скобок нет
                            # Выставляем роль и описание
                            dossier[ROLES].append(
                                (ctx.message.role_mentions[0].id, " ".join(ctx.args[2:]))
                            )
                    elif ctx.args[0] == "rename":
                        if next(filter(lambda x: x[0] == ctx.message.role_mentions[0].id, dossier[ROLES]),
                                None) is None:
                            return CommandResult.error("Такой роли не существует!")

                        for i, role_object in enumerate(dossier[ROLES]):
                            if role_object[0] == ctx.message.role_mentions[0].id:
                                dossier[ROLES][i] = (ctx.message.role_mentions[0].id, " ".join(ctx.args[2:]))

                                break

                    # Сохраняем всё
                    save_cache()

                    # Обновляем сообщение
                    embed = self.create_embed(ctx)
                    guild: discord.Guild = ctx.message.guild
                    channel: discord.TextChannel = guild.get_channel(dossier[CHANNEL_ID])

                    # Проверка на наличие сообщения
                    try:
                        msg: discord.Message = await channel.fetch_message(dossier[MESSAGE_ID])
                    except discord.NotFound:
                        # Обработка отсутствия
                        msg = await channel.send(embed=embed)

                        # Проставляем эмодзи
                        for i in range(len(dossier[ROLES])):
                            emoji = chr(EMOJI_START + i)

                            await msg.add_reaction(emoji)
                        return CommandResult.info(
                            message="Поскольку сообщение было удалено, автоматически было создано новое.",
                            title="Произошла ошибка, которая была автоматически разрешена.")
                    else:
                        await msg.edit(embed=embed)
                        # Удаляем лишние реакции

                        for reaction in msg.reactions:
                            reaction: discord.Reaction

                            if reaction.custom_emoji:
                                await reaction.clear()

                            if ord(reaction.emoji) not in range(EMOJI_START, EMOJI_START + len(dossier[ROLES])):
                                await reaction.clear()

                        # Проставляем недостающие.
                        for i in range(len(dossier[ROLES])):
                            emoji = chr(EMOJI_START + i)

                            if next(filter(lambda x: x.emoji == emoji, msg.reactions), None) is None:
                                await msg.add_reaction(emoji)

                return CommandResult.ok()

    async def on_event(self, event_name, *args, **kwargs):
        if event_name == "on_raw_reaction_add" or event_name == "on_raw_reaction_remove":
            payload: discord.RawReactionActionEvent = args[0]
        else:
            return

        if payload.user_id == self.bot.user.id:
            return

        # Проверка на сообщение на сервере
        if payload.guild_id is None:
            return

        # Проверка на то, что это искомое сообщение, на которое нужно ставить роли
        key = str(payload.guild_id)
        if key not in cache:
            return

        dossier = cache[key]
        if payload.message_id != dossier[MESSAGE_ID] or payload.channel_id != dossier[CHANNEL_ID]:
            return

        # Получение юзера
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        member: discord.Member = guild.get_member(payload.user_id)

        # Проверка, что роль не кастомная
        if payload.emoji.id is not None:
            return

        # Проверка на индекс
        roles = dossier[ROLES]
        index = ord(payload.emoji.name) - EMOJI_START
        if index not in range(len(roles)):
            return

        # Расходимся, это обманка.
        if roles[index][0] == -1:
            return

        # Получение роли
        role = guild.get_role(roles[index][0])

        # Установка
        if payload.event_type == "REACTION_ADD":
            await member.add_roles(role, reason="RoleReaction automatic system")
        elif payload.event_type == "REACTION_REMOVE":
            await member.remove_roles(role, reason="RoleReaction automatic system")
