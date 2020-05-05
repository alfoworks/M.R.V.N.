import asyncio
from urllib import parse

import aiohttp
import discord
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandContext, CommandResult, EmbedType

service_url = "https://visionbot.ru/index.php"


@mrvn_module("Vision", "Модуль для автоматического описания изображений.")
class VisionModule(Module):
    async def on_enable(self):
        @mrvn_command(self, "vs", "Распознавание объектов с картинки, примерное описание.", "<изображение>")
        class VsCommand(Command):
            @staticmethod
            async def image_scan_task(url, ctx):
                try:
                    async with aiohttp.ClientSession(timeout=ClientTimeout(20)) as session:
                        async with session.post(service_url, data="userlink=%s" % parse.quote(url, safe=''),
                                                headers={"Cookie": "textonly=true; imageonly=true; qronly=false",
                                                         "Content-Type": "application/x-www-form-urlencoded"}) as response:
                            text = await response.text()

                            soup = BeautifulSoup(text, "html.parser")
                            results = soup.find_all("div", {"class": "success description"})

                            if not len(results):
                                await ctx.send_embed(EmbedType.ERROR, "Не удалось получить результат распознования.")
                                return

                            embed: discord.Embed = ctx.get_embed(EmbedType.INFO, results[0].text,
                                                                 "Результат распознавания")
                            embed.set_image(url=url)

                            await ctx.message.channel.send(embed=embed)
                except aiohttp.ClientConnectionError:
                    await ctx.send_embed(EmbedType.ERROR, "Не удалось подключиться к серверу.")
                except asyncio.TimeoutError:
                    await ctx.send_embed(EmbedType.ERROR, "Превышено время ожидания.")

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if not len(ctx.message.attachments):
                    return CommandResult.args_error("Нет изображения.")

                attachment = ctx.message.attachments[0]

                if not attachment.filename.lower().endswith(("jpg", "gif", "png")):
                    return CommandResult.args_error("Приклеплённое вами вложение не является изображением.")

                await self.module.bot.module_handler.add_background_task(self.image_scan_task(attachment.url, ctx),
                                                                         self.module)

                return CommandResult.ok(wait_emoji=True)
