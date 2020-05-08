import asyncio
import difflib
import traceback
from datetime import timedelta

import discord

from decorators import mrvn_module
from modular import Module, CommandContext, EmbedType


@mrvn_module("KGB", "Модуль для отслеживания различных вещей.")
class KGBModule(Module):
    unremovable_messages = {}
    invites_cached = {}
    guild_id = 394132321839874050

    async def invite_caching_task(self):
        while True:
            self.invites_cached = self.invites_to_dict((await self.bot.get_guild(self.guild_id).invites()))

            await asyncio.sleep(10)

    async def on_enable(self):
        self.bot.module_handler.add_param("kgbmode", False)
        self.bot.module_handler.add_param("custom_join_msg", True)

        self.logger.info("Запуск таска обновления кеша инвайтов...")
        await self.bot.module_handler.add_background_task(self.invite_caching_task(), self)

    @staticmethod
    async def find_who_deleted(message):
        guild: discord.Guild = message.guild

        try:
            last_audit_action = await guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete).next()
        except discord.NoMoreItems:
            return None

        if last_audit_action.created_at < (message.created_at - timedelta(seconds=1)):
            return None

        if last_audit_action.extra.channel.id == message.channel.id:
            return last_audit_action.user

    @staticmethod
    def invites_to_dict(invites):
        result = {}

        for invite in invites:
            result[invite.code] = (invite.uses, invite)

        return result

    async def get_inviter(self):
        invites = self.invites_to_dict(await self.bot.get_guild(self.guild_id).invites())

        for code in list(invites.keys()):
            if invites[code][0] > self.invites_cached[code][0]:
                self.invites_cached = invites
                return invites[code][1].inviter

    async def on_event(self, event_name, *args, **kwargs):
        if event_name == "on_message_delete":
            message: discord.Message = args[0]

            if not message.guild:
                return

            if message.id in self.unremovable_messages:
                embed = self.unremovable_messages[message.id]
                del self.unremovable_messages[message.id]

                message_sent = await message.channel.send(embed=embed)
                self.unremovable_messages[message_sent.id] = embed

                return

            if not self.bot.module_handler.get_param("kgbmode"):
                return

            deleted_by = await self.find_who_deleted(message)

            embed: discord.Embed = CommandContext.get_custom_embed_static("",
                                                                          "%s удалил своё сообщение!" %
                                                                          message.author.display_name
                                                                          if deleted_by is None else
                                                                          "%s удалил сообщение %s!" % (
                                                                              deleted_by.display_name,
                                                                              message.author.display_name),
                                                                          0xfcef2e)

            embed.add_field(name="Сообщение:", value="<ничего>" if not len(message.content) else message.content)

            message_sent = await message.channel.send(embed=embed)
            self.unremovable_messages[message_sent.id] = embed
        elif event_name == "on_message_edit":
            message_before: discord.Message = args[0]
            message_after: discord.Message = args[1]

            if not message_after.guild:
                return

            if message_after.id in self.unremovable_messages and not len(message_after.embeds):
                embed = self.unremovable_messages[message_after.id]
                del self.unremovable_messages[message_after.id]

                message_sent = await message_after.channel.send(embed=embed)
                self.unremovable_messages[message_sent.id] = embed

                return

            if not self.bot.module_handler.get_param("kgbmode"):
                return

            if message_before.content == message_after.content:
                return

            if difflib.SequenceMatcher(None, message_before.content, message_after.content).ratio() > 0.6:
                return

            embed: discord.Embed = CommandContext.get_custom_embed_static("",
                                                                          "%s изменил своё сообщение!" %
                                                                          message_after.author.display_name,
                                                                          0xfcef2e)

            embed.add_field(name="Было:", value=message_before.content if len(message_before.content) else "<ничего>")
            embed.add_field(name="Стало:", value=message_after.content if len(message_after.content) else "<ничего>")

            message_sent = await message_after.channel.send(embed=embed)
            self.unremovable_messages[message_sent.id] = embed
        elif event_name == "on_member_remove":
            member: discord.Member = args[0]

            sys_channel: discord.TextChannel = member.guild.system_channel

            if not sys_channel:
                return

            embed: discord.Embed = CommandContext.get_custom_embed_static(
                "%s (%s#%s) вышел с сервера." % (member.mention, member.display_name, member.discriminator), "Инфо",
                EmbedType.ERROR.value[0])

            await sys_channel.send(embed=embed)
        elif event_name == "on_member_join":
            member: discord.Member = args[0]

            if not self.bot.module_handler.get_param(
                    "custom_join_msg") or member.guild.system_channel is None or \
                    member.guild.system_channel_flags.join_notifications:
                return

            sys_channel: discord.TextChannel = member.guild.system_channel
            inviter = None
            join_message = "%s вошёл на сервер!" % member.mention

            try:
                inviter = await self.get_inviter()
            except Exception:
                print(traceback.format_exc())

            if inviter is not None:
                join_message += " (пригласил: %s)" % inviter.mention

            embed: discord.Embed = CommandContext.get_custom_embed_static(join_message,
                                                                          "Инфо",
                                                                          EmbedType.OK.value[0])

            await sys_channel.send(embed=embed)
