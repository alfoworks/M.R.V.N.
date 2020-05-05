import asyncio
import os
import random

import aiohttp
import discord
from aiohttp import ClientTimeout

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext, EmbedType


@mrvn_module("ImageSearch", "Поиск изображений в Google с определением NSFW контента.")
class ImageSearchModule(Module):
    cx = None
    api_key = None

    async def on_enable(self):
        ImageSearchModule.cx = os.environ.get("mrvn_image_search_cx")
        ImageSearchModule.api_key = os.environ.get("mrvn_image_search_apikey")

        if ImageSearchModule.cx is None or ImageSearchModule.api_key is None:
            self.logger.error("[ImageSearch] CX и/или API ключ недоступны. Проверьте \"kaizen_image_search_cx\" и "
                              "\"kaizen_image_search_apikey\" в PATH.")

        @mrvn_command(self, "img", "Поиск изображений в Google.", "<поисковый запрос> [--index=<индекс 0 - 4>]")
        class ImgCommand(Command):
            @staticmethod
            async def image_task(ctx, keyword, index):
                try:
                    async with aiohttp.ClientSession(timeout=ClientTimeout(20)) as session:
                        async with session.get("https://www.googleapis.com/customsearch/v1",
                                               params={"q": keyword, "num": 5, "start": 1, "searchType": "image",
                                                       "key": ImageSearchModule.api_key,
                                                       "cx": ImageSearchModule.cx}) as response:

                            data = await response.json()

                            if response.status != 200:
                                if data["error"]["status"] == "RESOURCE_EXHAUSTED":
                                    await ctx.send_embed(EmbedType.ERROR,
                                                         "Команда временно недоступна, так как было превышено "
                                                         "количество запросов к API у бота. Попробуйте "
                                                         "выполнить её позже.")
                                else:
                                    await ctx.send_embed(EmbedType.ERROR,
                                                         "Произошла ошибка API:\n%s" % data["error"]["status"])
                                return

                            if data["searchInformation"]["totalResults"] == "0":
                                await ctx.send_embed(EmbedType.ERROR,
                                                     "Картинка по запросу \"%s\" не найдена!" % keyword)
                                return

                            max_index = len(data["items"]) - 1

                            r_index = random.randrange(max_index + 1) if index is None else (
                                0 if index not in range(max_index + 1) else index)

                            image = data["items"][r_index]

                            embed: discord.Embed = ctx.get_embed(EmbedType.OK, "",
                                                                 "Картинка по запросу \"%s\" (индекс: %s)" % (
                                                                     keyword, r_index))
                            embed.set_author(name=image["title"], url=image["image"]["contextLink"],
                                             icon_url=image["image"]["thumbnailLink"])
                            embed.set_image(url=image["link"])

                            await ctx.message.channel.send(embed=embed)
                except (asyncio.TimeoutError, aiohttp.ClientConnectionError):
                    await ctx.send_embed(EmbedType.ERROR, "Не удалось подключиться к серверу.")

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if ImageSearchModule.cx is None or ImageSearchModule.api_key is None:
                    return CommandResult.error(
                        "Команда не работает, так как API ключ и/или CX "
                        "недоступны. Возможно, бот запущен не в продакшн-среде.")

                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()

                index = None

                if len(ctx.keys) != 0 and ctx.keys[0].startswith("index="):
                    try:
                        index = int(ctx.keys[0].split("index=")[1])
                    except ValueError:
                        pass

                await self.module.bot.module_handler.add_background_task(
                    self.image_task(ctx, " ".join(ctx.clean_args), index),
                    self.module)

                return CommandResult.ok(wait_emoji=True)
