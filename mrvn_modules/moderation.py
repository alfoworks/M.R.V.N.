import asyncio
import time

import discord

from decorators import mrvn_module, mrvn_command
from modular import Module, DiscordPermissionHandler, Command, CommandContext, CommandResult, LanguageUtils, EmbedType

MUTED_ROLE_ID = 397808474320404482
MODLOG_CHANNEL_ID = 485572652099174401

declensions_dict: dict = {'s': ["секунду", "секунды", "секунд"], 'm': ["минуту", "минуты", "минут"],
                          'h': ["час", "часа", "часов"], 'd': ["день", "дня", "дней"],
                          'w': ["неделю", "недели", "недель"]}


def pluralize_russian(number, nom_sing, gen_sing, gen_pl):
    s_last_digit = str(number)[-1]

    if int(str(number)[-2:]) in range(5, 20) or int(s_last_digit) == "0":
        # 11-19, 0
        return gen_pl
    elif s_last_digit == '1':
        # 1
        return nom_sing
    elif int(s_last_digit) in range(2, 5):
        # 2,3,4
        return gen_sing
    # unreached
    return gen_pl


class MutedUser:
    user_id = 0
    guild_id = 0
    deadline = 0

    roles = []

    def __init__(self, user_id, guild_id, roles, deadline):
        self.user_id = user_id
        self.guild_id = guild_id
        self.roles = roles
        self.deadline = deadline


class UserWarn:
    guild_id = 0

    def __init__(self, guild_if):
        self.guild_id = guild_if


@mrvn_module("Moderation", "Модуль для модерации.")
class ModerationModule(Module):
    async def tempmute_task(self):
        while True:
            for muted_user in self.bot.module_handler.params["moderation_mutes"]:
                if muted_user.deadline != 0 and muted_user.deadline < time.time():
                    self.bot.module_handler.params["moderation_mutes"].remove(muted_user)
                    self.bot.module_handler.save_params()

                    guild: discord.Guild = self.bot.get_guild(muted_user.guild_id)
                    role: discord.Role = guild.get_role(MUTED_ROLE_ID)
                    member: discord.Member = guild.get_member(muted_user.user_id)

                    if role not in member.roles:
                        return

                    for taken_role in muted_user.roles:
                        if guild.get_role(taken_role):
                            await member.add_roles(guild.get_role(taken_role))

                    await member.remove_roles(role, reason="Unmute: timed out")
                    await self.bot.get_channel(MODLOG_CHANNEL_ID).send(
                        embed=CommandContext.get_custom_embed_static(
                            "С %s был снят мут по причине \"закончилось время мута\""
                            % member.mention, "Наказания", EmbedType.OK.value[0]))

            await asyncio.sleep(1)

    async def on_enable(self):
        self.bot.module_handler.add_param("moderation_mutes", [])

        await self.bot.module_handler.add_background_task(self.tempmute_task(), self)

        @mrvn_command(self, "purge",
                      "Удалить заданное количество сообщений. Из этого количества при указании пользователя удалит "
                      "все его сообщения.",
                      "<1 - 100> [@пользователь]", perm_handler=DiscordPermissionHandler(["manage_messages"]))
        class PurgeCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                try:
                    limit = int(ctx.args[0])
                except ValueError:
                    return CommandResult.args_error("Вы указали не число.")

                if limit not in range(100):
                    return CommandResult.args_error("Вы указали число меньше 1 или больше 100.")

                def check(msg):
                    return True if len(ctx.message.mentions) < 1 else msg.author == ctx.message.mentions[0]

                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass

                deleted = await ctx.message.channel.purge(limit=limit, check=check)

                await ctx.send_embed(EmbedType.ERROR,
                                     "%s удалил %s из канала %s." % (ctx.message.author.mention,
                                                                     pluralize_russian(
                                                                         len(deleted),
                                                                         "сообщение",
                                                                         "сообщения",
                                                                         "сообщений"),
                                                                     ctx.message.channel), "Очистка сообщений",
                                     self.module.bot.get_channel(MODLOG_CHANNEL_ID), sign=False)

                return CommandResult.ok("Удалено %s." % (
                    LanguageUtils.pluralize(len(deleted),
                                            "сообщение",
                                            "сообщения",
                                            "сообщений")))

        @mrvn_command(self, "mute", "Выдать перманентный мут пользователю.", "<@пользователь> [причина]",
                      perm_handler=DiscordPermissionHandler(["manage_roles"]))
        class MuteCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.message.mentions) < 1:
                    return CommandResult.args_error("Пользователь не указан.")

                if ctx.message.mentions[0] == self.module.bot.user:
                    return CommandResult.error("Меня нельзя замутить :)")

                if ctx.message.mentions[0] == ctx.message.author:
                    return CommandResult.error("Вы не можете замутить самого себя!")

                role = ctx.message.guild.get_role(MUTED_ROLE_ID)

                if role is None:
                    return CommandResult.error("Роль мута с ID %s не найдена!" % MUTED_ROLE_ID)

                if role in ctx.message.mentions[0].roles:
                    return CommandResult.error("Этот пользователь уже в муте!")

                if ctx.message.author.top_role.position < ctx.message.mentions[
                    0].top_role.position and ctx.message.author.guild_permissions > ctx.message.mentions[
                    0].guild_permissions:
                    return CommandResult.error("Вы не можете замутить этого пользователя.")

                reason = "Плохое поведение"
                roles = []

                if len(ctx.args) > 1:
                    reason = " ".join(ctx.args[1:])

                await ctx.message.mentions[0].add_roles(role, reason=reason)

                for member_role in ctx.message.mentions[0].roles:
                    if member_role != role and member_role.id != ctx.message.guild.id:
                        await ctx.message.mentions[0].remove_roles(member_role)
                        roles.append(member_role.id)

                await ctx.send_embed(EmbedType.ERROR, "%s был заткнут %s по причине \"%s\"." % (
                    ctx.message.mentions[0].mention, ctx.message.author.mention, reason),
                                     "Наказания", self.module.bot.get_channel(MODLOG_CHANNEL_ID), sign=False)

                for user in self.module.bot.module_handler.get_param("moderation_mutes"):
                    if user.user_id == ctx.message.mentions[0].id:
                        return CommandResult.ok()

                muted_user = MutedUser(ctx.message.mentions[0].id, ctx.message.author.guild.id,
                                       roles, 0)
                self.module.bot.module_handler.params["moderation_mutes"].append(muted_user)
                self.module.bot.module_handler.save_params()

                return CommandResult.ok()

        @mrvn_command(self, "tempmute", "Выдать временный мут пользователю.",
                      "<@пользователь> <длительность> <s/m/h/d/w> [причина]",
                      perm_handler=DiscordPermissionHandler(["manage_roles"]))
        class CommandTempMute(Command):
            duration_variants = {"s": 1, "m": 60, "h": 3600, "d": 84600, "w": 592200}

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.message.mentions) < 1:
                    return CommandResult.args_error("Пользователь не указан.")

                if ctx.message.mentions[0] == self.module.bot.user:
                    return CommandResult.error("Меня нельзя замутить :)")

                if ctx.message.mentions[0] == ctx.message.author:
                    return CommandResult.error("Вы не можете замутить самого себя!")

                role = ctx.message.guild.get_role(MUTED_ROLE_ID)

                if role is None:
                    return CommandResult.error("Роль мута с ID %s не найдена!" % MUTED_ROLE_ID)

                if role in ctx.message.mentions[0].roles:
                    return CommandResult.error("Этот пользователь уже в муте!")

                if ctx.message.author.top_role.position < ctx.message.mentions[
                    0].top_role.position and ctx.message.author.guild_permissions > ctx.message.mentions[
                    0].guild_permissions:
                    return CommandResult.error("Вы не можете замутить этого пользователя.")

                reason = "Плохое поведение"
                roles = []

                try:
                    duration = int(ctx.args[1])
                except ValueError:
                    return CommandResult.args_error("Вы указали не число.")

                if ctx.args[2].lower() not in self.duration_variants:
                    return CommandResult.args_error("Вы указали неверную единицу времени.")

                deadline = time.time() + duration * self.duration_variants[ctx.args[2].lower()]

                if len(ctx.args) > 3:
                    reason = " ".join(ctx.args[3:])

                await ctx.message.mentions[0].add_roles(role, reason=reason)

                for member_role in ctx.message.mentions[0].roles:
                    if member_role != role and member_role.id != ctx.message.guild.id:
                        await ctx.message.mentions[0].remove_roles(member_role)
                        roles.append(member_role.id)

                declensions = declensions_dict[ctx.args[2].lower()]
                unit = pluralize_russian(duration, declensions[0], declensions[1], declensions[2])

                await ctx.send_embed(EmbedType.ERROR, "%s был заткнут %s по причине \"%s\" на %s %s." % (
                    ctx.message.mentions[0].mention,
                    ctx.message.author.mention,
                    reason,
                    duration,
                    unit),
                                     "Наказания", self.module.bot.get_channel(MODLOG_CHANNEL_ID), sign=False)

                for user in list(self.module.bot.module_handler.params["moderation_mutes"]):
                    if user.user_id == ctx.message.mentions[0].id:
                        self.module.bot.module_handler.params["moderation_mutes"].remove(user)

                muted_user = MutedUser(ctx.message.mentions[0].id, ctx.message.author.guild.id,
                                       roles, deadline)

                self.module.bot.module_handler.params["moderation_mutes"].append(muted_user)
                self.module.bot.module_handler.save_params()

                return CommandResult.ok()

        @mrvn_command(self, "unmute", "<@пользователь>", perm_handler=DiscordPermissionHandler(["manage_roles"]))
        class CommandUnmute(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.message.mentions) < 1:
                    return CommandResult.args_error("Пользователь не указан.")

                role = ctx.message.guild.get_role(MUTED_ROLE_ID)

                if role is None:
                    return CommandResult.error("Роль мута с ID %s не найдена!" % MUTED_ROLE_ID)

                if role not in ctx.message.mentions[0].roles:
                    return CommandResult.error("Этот пользователь не в муте!")

                await ctx.message.mentions[0].remove_roles(role, reason="Unmute")

                await ctx.send_embed(EmbedType.OK, "%s снял мут с %s." % (
                    ctx.message.author.mention, ctx.message.mentions[0].mention), "Наказания",
                                     self.module.bot.get_channel(MODLOG_CHANNEL_ID), sign=False)

                for user in list(self.module.bot.module_handler.params["moderation_mutes"]):
                    if user.user_id == ctx.message.mentions[0].id:
                        self.module.bot.module_handler.params["moderation_mutes"].remove(user)
                        self.module.bot.module_handler.save_params()

                        for role_id in user.roles:
                            if ctx.message.guild.get_role(role_id):
                                await ctx.message.mentions[0].add_roles(ctx.message.guild.get_role(role_id))
                        return CommandResult.ok()

                return CommandResult.ok()

    async def on_discord_event(self, event_name, *args, **kwargs):
        if event_name != "on_member_join":
            return

        member = args[0]

        for user in self.bot.module_handler.params["moderation_mutes"]:
            if user.user_id == member.id and member.guild.id == user.guild_id:
                await member.add_roles(member.guild.get_role(MUTED_ROLE_ID), reason="User is muted")
                break
