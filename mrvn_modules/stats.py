import asyncio
import json
import os
from github import Github

import discord

from decorators import mrvn_command, mrvn_module, command_listener
from modular import Command, Module, CommandResult, CommandContext, EmbedType, CommandListener
from mrvn_config import MrvnConfig

stats = {
    "processed_commands": 0,
    "command_top": {},
    "user_top": {}
}


@mrvn_module("Stats", "Модуль для статистики по командам.")
class StatsModule(Module):
    stats_file = "mrvn_stats.json"

    def write_data(self):
        with open(self.stats_file, "w") as f:
            json.dump(stats, f)

    async def stats_save_task(self):
        while True:
            self.write_data()

            await asyncio.sleep(120)

    async def on_enable(self):
        if not os.path.isfile(self.stats_file):
            self.write_data()
            self.logger.ok("Создан JSON файл статистики.")
        else:
            with open(self.stats_file, "r") as f:
                global stats
                stats = json.load(f)

        await self.bot.module_handler.add_background_task(self.stats_save_task(), self)
        self.logger.info("Запуск таск сохранения статистики...")

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

        @mrvn_command(self, "gitcommits", "Показывает статистику по коммитам организации alfoworks.", "<repo>",
                      ['type=<any/style/feature/fix/refactor>'])
        class GitCommitsCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()
                g = Github(MrvnConfig.github_login, MrvnConfig.github_password)
                if ctx.clean_args[0] in [n.full_name.split("/")[1] for n in g.get_organization("alfoworks").get_repos()]:
                    comms = [i.commit for i in
                             list(g.get_organization("alfoworks").get_repo(ctx.clean_args[0]).get_commits())]
                    comm_messages = [l.message for l in comms]
                    embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "",
                                                         "Статистика коммитов по репозиторию %s" % ctx.clean_args[0])
                    embed.add_field(name="**Всего коммитов обработано:**", value=len(comms), inline=False)

                    def typecheck(comm_type):
                        type_comms = []
                        last_comms = ""
                        for m in comm_messages:
                            if "[" + comm_type.upper() + "]" in m:
                                type_comms.append(m)
                        for k in type_comms[0:5]:
                            last_comms += "%s\n\n" % k
                        embed.add_field(name="**Последние [" + comm_type.upper() + "] коммиты:**", value=last_comms,
                                        inline=False)

                    if "type" not in ctx.keys:
                        last_comms = ""
                        for k in comm_messages[0:5]:
                            last_comms += "%s\n\n" % k
                        embed.add_field(name="**Последние коммиты:**", value=last_comms, inline=False)
                    elif "type" in ctx.keys:
                        if ctx.keys['type'].lower() in ["any", "style", "feature", "fix", "refactor"]:
                            typecheck(ctx.keys['type'])
                        else:
                            last_comms = ""
                            for k in comm_messages[0:5]:
                                last_comms += "%s\n\n" % k
                            embed.add_field(name="**Последние коммиты:**", value=last_comms, inline=False)
                    await ctx.message.channel.send(embed=embed)

                    return CommandResult.ok()
                else:
                    return CommandResult.error("Репозитория %s не существует!" % ctx.clean_args[0])

        @command_listener(self)
        class StatsCommandListener(CommandListener):
            async def on_command_execute(self, command: Command, result: CommandResult, ctx: CommandContext):
                if ctx.message.channel.id == 394134985482960907:  # Если вы не знали - то лень выглядит именно так.
                    return

                name = command.name
                usver_id = str(ctx.message.author.id)

                stats["command_top"][name] = 1 if name not in stats["command_top"] else stats["command_top"][name] + 1

                stats["user_top"][usver_id] = {
                    "commands_used": 1 if usver_id not in stats["user_top"] else stats["user_top"][usver_id][
                                                                                     "commands_used"] + 1,
                    "display_name": ctx.message.author.display_name
                }

                stats["processed_commands"] = stats["processed_commands"] + 1
