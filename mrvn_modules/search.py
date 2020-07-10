import asyncio
import json
import os
import random
import urllib.parse
import urllib.request

import aiohttp
import discord
import requests
import wikipedia as wikipedia
from aiohttp import ClientTimeout

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandContext, CommandResult, EmbedType


@mrvn_module("Search", "Поиск информации на таких сайтах, как Wikipedia, GoogleImages и YouTube.")
class SearchModule(Module):
    cx = None
    api_key = None

    async def on_enable(self):
        SearchModule.cx = os.environ.get("mrvn_image_search_cx")
        SearchModule.api_key = os.environ.get("mrvn_image_search_apikey")

        if SearchModule.cx is None or SearchModule.api_key is None:
            self.logger.error("[ImageSearch] CX и/или API ключ недоступны. Проверьте \"kaizen_image_search_cx\" и "
                              "\"kaizen_image_search_apikey\" в PATH.")

        wikipedia.set_lang("ru")

        @mrvn_command(self, "yt", "Поиск видео в YouTube.", "<поисковый запрос>")
        class YTCommand(Command):
            class YoutubeSearch:
                def __init__(self, search_terms: str, max_results=None):
                    self.search_terms = search_terms
                    self.max_results = max_results
                    self.videos = self.search()

                def search(self):
                    encoded_search = urllib.parse.quote(self.search_terms)
                    base_url = "https://youtube.com"
                    url = f"{base_url}/results?search_query={encoded_search}"
                    response = requests.get(url).text
                    while 'window["ytInitialData"]' not in response:
                        response = requests.get(url).text
                    results = self.parse_html(response)
                    if self.max_results is not None and len(results) > self.max_results:
                        return results[: self.max_results]
                    return results

                def parse_html(self, response):
                    results = []
                    start = (
                            response.index('window["ytInitialData"]')
                            + len('window["ytInitialData"]')
                            + 3
                    )
                    end = response.index("};", start) + 1
                    json_str = response[start:end]
                    data = json.loads(json_str)

                    videos = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
                        "sectionListRenderer"
                    ]["contents"][0]["itemSectionRenderer"]["contents"]

                    for video in videos:
                        res = {}
                        if "videoRenderer" in video.keys():
                            video_data = video["videoRenderer"]
                            res["id"] = video_data["videoId"]
                            res["thumbnails"] = [
                                thumb["url"] for thumb in video_data["thumbnail"]["thumbnails"]
                            ]
                            res["title"] = video_data["title"]["runs"][0]["text"]
                            res["channel"] = video_data["longBylineText"]["runs"][0]["text"]
                            res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                            res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
                            res["url_suffix"] = video_data["navigationEndpoint"]["commandMetadata"][
                                "webCommandMetadata"
                            ]["url"]
                            results.append(res)
                    return results

                def to_dict(self):
                    return self.videos

                def to_json(self):
                    return json.dumps({"videos": self.videos})

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                keyword = " ".join(ctx.clean_args)

                results = self.YoutubeSearch(keyword, max_results=1).to_dict()

                if len(results) < 1:
                    return CommandResult.error("Видео по этому запросу не найдено.")

                await ctx.message.channel.send("Видео по запросу \"%s\": (запросил: %s)\n%s" % (
                    keyword, ctx.message.author.mention, "https://youtube.com/" + results[0]["url_suffix"]))
                return CommandResult.ok()

                """
                url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(keyword)
                response = urllib.request.urlopen(url)
                html = response.read()
                soup = BeautifulSoup(html, 'html.parser')

                for vid in soup.findAll(attrs={'class': 'yt-uix-tile-link'}):
                    vid_url = "https://www.youtube.com" + vid["href"]

                    if "channel" not in vid_url:
                        await ctx.message.channel.send("Видео по запросу \"%s\": (запросил: %s)\n%s" % (
                            keyword, ctx.message.author.mention, vid_url))
                        return CommandResult.ok()

                return CommandResult.error("Видео по этому запросу не найдено.")
                """

        @mrvn_command(self, "img", "Поиск изображений в Google.", "<поисковый запрос> [--index=<индекс 0 - 4>]")
        class ImgCommand(Command):
            @staticmethod
            async def image_task(ctx, keyword, index):
                try:
                    async with aiohttp.ClientSession(timeout=ClientTimeout(20)) as session:
                        async with session.get("https://www.googleapis.com/customsearch/v1",
                                               params={"q": keyword, "num": 5, "start": 1, "searchType": "image",
                                                       "key": SearchModule.api_key,
                                                       "cx": SearchModule.cx}) as response:

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
                if SearchModule.cx is None or SearchModule.api_key is None:
                    return CommandResult.error(
                        "Команда не работает, так как API ключ и/или CX "
                        "недоступны. Возможно, бот запущен не в продакшн-среде.")

                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()

                index = None
                try:
                    index = int(ctx.keys["index"])
                except ValueError:
                    pass
                except KeyError:
                    pass
                # if len(ctx.raw_keys) != 0 and ctx.raw_keys[0].startswith("index="):
                #     try:
                #         index = int(ctx.raw_keys[0].split("index=")[1])
                #     except ValueError:
                #         pass

                await self.module.bot.module_handler.add_background_task(
                    self.image_task(ctx, " ".join(ctx.clean_args), index),
                    self.module)

                return CommandResult.ok(wait_emoji=True)

        @mrvn_command(self, "wiki", "Поиск информации в Wikipedia.", "<поисковый запрос>")
        class WikiCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()

                query = " ".join(ctx.clean_args)

                nf_the_search = wikipedia.search(query, results=1)

                if len(nf_the_search) == 0:
                    return CommandResult.error("По запросу \"%s\" ничего не найдено." % query)

                title = nf_the_search[0]

                while True:
                    try:
                        text = wikipedia.summary(title, sentences=4)
                    except wikipedia.DisambiguationError as e:
                        title = e.options[0]
                    else:
                        break

                page = wikipedia.page(title)

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, text, page.title)
                if len(page.images) > 0:
                    embed.set_image(url=page.images[0])

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()
