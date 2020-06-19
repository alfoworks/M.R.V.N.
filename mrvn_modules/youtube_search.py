import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandContext, CommandResult


@mrvn_module("YoutubeSearch", "Поиск видео в YouTube.")
class YoutubeModule(Module):
    async def on_enable(self):
        @mrvn_command(self, "yt", "Поиск видео в YouTube.", "<поисковый запрос>")
        class YTCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                keyword = " ".join(ctx.clean_args)

                url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(keyword)
                response = urllib.request.urlopen(url)
                html = response.read()
                soup = BeautifulSoup(html, 'html.parser')

                for vid in soup.findAll(attrs={'class': 'yt-uix-tile-link'}):
                    vid_url = "https://www.youtube.com" + vid["href"]

                    if "channel" not in vid_url:
                        await ctx.message.channel.send("Видео по запросу \"%s\": (запросил: %s)\n%s" % (keyword, ctx.message.author.mention, vid_url))
                        return CommandResult.ok()


                return CommandResult.error("Видео по этому запросу не найдено.")
