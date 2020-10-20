import asyncio
import datetime
import json
import os
import time
from github import Github, GithubObject
from github import UnknownObjectException
import github

import discord

from decorators import mrvn_command, mrvn_module, command_listener
from modular import Command, Module, CommandResult, CommandContext, EmbedType, CommandListener, LanguageUtils

stats = {
    "processed_commands": 0,
    "command_top": {},
    "user_top": {},
    "activity_top": {}
}


@mrvn_module("Stats", "Модуль для статистики по командам.")
class StatsModule(Module):
    stats_file = "mrvn_stats.json"
    github_token = None

    def write_data(self):
        with open(self.stats_file, "w") as f:
            json.dump(stats, f)

    async def stats_save_task(self):
        while True:
            self.write_data()

            await asyncio.sleep(120)

    async def on_event(self, event_name, *args, **kwargs):
        if event_name != "on_member_update":
            return

        member: discord.Member = args[0]

        if not len(member.activities):
            return

        if member.guild.id not in stats["activity_top"]:
            stats["activity_top"][member.guild.id] = {}

        for activity in member.activities:
            # stats["activity_top"][member.guild.id][activity].
            if activity.type == discord.ActivityType.custom:
                continue

            name = "Spotify" if isinstance(activity, discord.Spotify) else activity.name

            if name not in stats["activity_top"][member.guild.id]:
                stats["activity_top"][member.guild.id][name] = [member.id]
            elif member.id not in stats["activity_top"][member.guild.id][name]:
                stats["activity_top"][member.guild.id][name].add(member.id)

    async def on_enable(self):
        if not os.path.isfile(self.stats_file):
            self.write_data()
            self.logger.ok("Создан JSON файл статистики.")
        else:
            with open(self.stats_file, "r") as f:
                global stats
                stats = json.load(f)

            if "activity_top" not in stats:  # Потому что в уже существующих жсонах этого нет
                stats["activity_top"] = {}

        await self.bot.module_handler.add_background_task(self.stats_save_task(), self)
        self.logger.info("Запуск таск сохранения статистики...")

        StatsModule.github_token = os.environ.get("mrvn_gitcommits_token")

        if StatsModule.github_token is None:
            self.logger.error("Github токен не указан.")

        @mrvn_command(self, "actstats",
                      "Показывает статистику по активностям пользователей в их статусе (Играет, Слушает и пр.)")
        class ActStatsCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if ctx.message.guild.id not in stats["activity_top"]:
                    return CommandResult.error("Ещё неизвестно!")

                activity_stats = stats["activity_top"][ctx.message.guild.id]

                sorted_top = {k: v for k, v in sorted(activity_stats.items(), key=lambda item: len(item[1]))}

                top_text = ""

                i = 1
                for k, v in sorted_top.items():
                    top_text += "**%s.** %s (%s)\n" % (
                        i, k, LanguageUtils.pluralize(len(v), "пользователь", "пользователя", "пользователей"))

                    i += 1

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "", "Статистика активности")
                embed.add_field(name="Топ активностей по кол-ву участников сервера", value=top_text)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, "stats", "Показывает статистику бота.")
        class StatsCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                commands_field = ""
                users_field = ""

                if len(stats["command_top"].values()):
                    sorted_top = {k: v for k, v in
                                  sorted(stats["command_top"].items(), key=lambda item: item[1],
                                         reverse=True)}

                    for i, k in enumerate(sorted_top):
                        commands_field += "**%s.** `%s` - %s\n" % (i + 1, k, sorted_top[k])

                        if i > 9:
                            break
                else:
                    commands_field = "Ещё неизвестно."

                top_user_avatar = None

                if len(stats["user_top"].values()):
                    sorted_top = {k: v for k, v in
                                  sorted(stats["user_top"].items(), key=lambda item: item[1]["commands_used"],
                                         reverse=True)}

                    for i, k in enumerate(sorted_top):
                        user = await self.module.bot.fetch_user(int(k))

                        if i == 0 and user is not None:
                            top_user_avatar = user.avatar_url

                        users_field += "**%s.** %s - %s\n" % (
                            i + 1, sorted_top[k]["display_name"] + " (недоступен)" if not user else user.mention,
                            sorted_top[k]["commands_used"])

                        if i > 9:
                            break
                else:
                    users_field = "Еще неизвестно."

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "", "Статистика бота %s" % self.module.bot.name)

                embed.add_field(name="**Всего команд обработано:**", value=stats["processed_commands"], inline=False)
                embed.add_field(name="**Топ используемых команд:**",
                                value=commands_field, inline=False)
                embed.add_field(name="**Топ пользователей по командам:**", value=users_field, inline=False)

                if top_user_avatar is not None:
                    embed.set_thumbnail(url=top_user_avatar)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, "gitcommits", "Показывает статистику по коммитам из GitHub.", "<repo>",
                      ["search-by=<message>"])
        class GitCommitsCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()

                if StatsModule.github_token is None:
                    return CommandResult.error("Команда не работает, т.к. не указан Github токен.")

                g = Github(StatsModule.github_token)

                try:
                    time_now = datetime.datetime.utcnow()

                    commits = ["%s - **%s** (*%s*)" % (x.message.split("\n\n")[0], x.author.name, (
                            LanguageUtils.formatted_duration(
                                int((time_now - x.committer.date).total_seconds()), 0) + " назад"))
                               for x in
                               [i.commit for i in
                                g.get_repo(
                                    ctx.clean_args[0]).get_commits()[0:5]]]

                    embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "",
                                                         "Статистика коммитов по репозиторию %s" % ctx.clean_args[0])
                    embed.add_field(name="**Всего коммитов:**",
                                    value=str(g.get_repo(ctx.clean_args[0]).get_commits().totalCount),
                                    inline=False)

                    if "search-by" in ctx.keys:
                        comm_msg = ctx.keys["search-by"].lower()

                        commits = []
                        start_time = time.time()

                        for commit in g.get_repo(ctx.clean_args[0]).get_commits():
                            message = commit.commit.message.split("\n\n")[0]

                            if time.time() - start_time >= 3:
                                break

                            if comm_msg in message.lower():
                                commits.append(message)

                                if len(commits) == 5:
                                    break

                        if len(commits) == 0:
                            return CommandResult.error("Не удалось найти коммиты с таким сообщением.")

                        message = "**Последние коммиты с cообщением \"%s\":**" % comm_msg
                    else:
                        message = "**Последние коммиты:**"

                    embed.add_field(name=message, value="\n\n".join(commits[0:5]),
                                    inline=False)

                    await ctx.message.channel.send(embed=embed)
                    return CommandResult.ok()
                except UnknownObjectException:
                    return CommandResult.error("Репозитория %s не существует!" % ctx.clean_args[0])

        @command_listener(self)
        class StatsCommandListener(CommandListener):
            async def on_command_execute(self, command: Command, result: CommandResult, ctx: CommandContext):
                name = command.name
                usver_id = str(ctx.message.author.id)

                stats["command_top"][name] = 1 if name not in stats["command_top"] else stats["command_top"][name] + 1

                stats["user_top"][usver_id] = {
                    "commands_used": 1 if usver_id not in stats["user_top"] else stats["user_top"][usver_id][
                                                                                     "commands_used"] + 1,
                    "display_name": ctx.message.author.display_name
                }

                stats["processed_commands"] = stats["processed_commands"] + 1
