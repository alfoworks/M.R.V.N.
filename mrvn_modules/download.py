from decorators import mrvn_module, mrvn_command
from modular import Module, LanguageUtils, Command, CommandResult, CommandContext, EmbedType
import requests
import json
import os
import discord


@mrvn_module(
            "download", 
            "Модуль для скачивания и отправки видео и аудио файлов с разых ресурсов(пока реализована только поддержка coub.com).")
class DownloadModule(Module):
    async def on_enable(self):

        @mrvn_command(
                    self, 
                    "coub", 
                    "Команда для парсинга ссылки на коуб для просмотра(или прослушки) его в дискорде.", 
                    "<Ссылка на коуб> <Video/Music>(стандартно Video)")
        class CoubCommand(Command):
            @staticmethod
            def parse_link(link, type = "video"):
                link = "http://coub.com//api/v2/coubs" + link[21:]
                response = {}
                r = requests.get(link)
                s = r.json()
                response["title"] = s["title"]
                response["content"] = s["file_versions"]["html5"]["audio"]["high"]["url"] if type == "music" else s["file_versions"]["share"]["default"]
                response["type"] = "mp3" if type == "music" else "mp4"
                return response
            

            @staticmethod
            def download_coub(response):
                res = requests.get(response["content"])
                open("file." + response["type"], "wb").write(res.content)
                

            @staticmethod
            def delete_coub(response):
                os.remove("file." + response["type"])
            

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()
                elif len(ctx.args) > 1:
                    if ctx.clean_args[1] != "video" and ctx.clean_args[1] != "music":
                        return CommandResult.error("Второй аргумент должен быть <video> или <music>")
                  

                try:
                    response = self.parse_link(ctx.clean_args[0], ctx.clean_args[1] if len(ctx.clean_args) > 1 else "video")
                except ValueError:
                    return CommandResult.error("Указанная ссылка не работает.")
                

                try:
                    self.download_coub(response)
                except OSError:
                    return CommandResult.error("Ошибка скачивания коуба.")


                await ctx.send_embed(EmbedType.INFO, response["title"], "Коуб успешно преобразован!")
                await ctx.message.channel.send(file = discord.File("file." + response["type"]))
                

                self.delete_coub(response)
                return CommandResult.ok()