from decorators import mrvn_module, mrvn_command
from modular import Module, LanguageUtils, Command, CommandResult, CommandContext, EmbedType
import requests
import json
import os
import discord
from pytube import YouTube
import pytube
from pydub import AudioSegment

class FileTooLarge(Exception):
    def __init__(self, required_size, size):
        self.message = "Файл слишком большой. Итоговый файл был бы весом {}, когда максимальный допустимый размер {}.".format(size, required_size)
        super().__init__(message)


@mrvn_module(
            "download", 
            "Модуль для скачивания и отправки видео и аудио файлов с разых ресурсов(пока реализована только поддержка coub.com).")
class DownloadModule(Module):

    @staticmethod
    def delete_file(file_type):
        os.remove("file." + file_type)

    @staticmethod
    def convert_file(response):
        song = AudioSegment.from_file("file." + response["type"])
        song.export("file.mp3", format = "mp3")
        DownloadModule.delete_file(response["type"])
        response["type"] = "mp3"
        return response

    async def on_enable(self):

        @mrvn_command(
                    self, 
                    "coub", 
                    "Команда для парсинга ссылки на коуб для просмотра(или прослушки) его в дискорде.", 
                    "<Ссылка на коуб> <Video/Music>(стандартно Video)")
        class CoubCommand(Command):
            @staticmethod
            def parse_link_coub(link, type = "video"):
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
            

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()
                elif len(ctx.args) > 1:
                    if ctx.clean_args[1] != "video" and ctx.clean_args[1] != "music":
                        return CommandResult.error("Второй аргумент должен быть <video> или <music>")
                  

                try:
                    response = self.parse_link_coub(ctx.clean_args[0], ctx.clean_args[1] if len(ctx.clean_args) > 1 else "video")
                except ValueError:
                    return CommandResult.error("Указанная ссылка не работает.")
                except KeyError:
                    return CommandResult.error("Указанная ссылка не работает.")

                try:
                    self.download_coub(response)
                except OSError:
                    return CommandResult.error("Ошибка записи коуба.")
                except requests.RequestException:
                    return CommandResult.error("Ошибка скачивания коуба.")

                await ctx.message.channel.send(
                                            "Коуб успешно преобразован.\n{}\n(Заказал: {})".format(response["title"], ctx.message.author.mention), 
                                            file = discord.File("file." + response["type"]))
                
                DownloadModule.delete_file(response["type"])

                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass

                return CommandResult.ok()

        @mrvn_command(
                    self, 
                    "tube", 
                    "Команда для парсинга ссылки на ютуб для просмотра(или прослушки) его в дискорде.", 
                    "<Ссылка на видео с ютуб> <Video/Music>(стандартно Video)")
        class TubeCommand(Command):


            @staticmethod
            def download_tube(link, type = "video"):
                yt = YouTube(link)
                response = {}
                streams = yt.streams.filter(
                                        only_audio = False if type == "video" else True, 
                                        file_extension = "mp4" if type == "video" else "webm").order_by("audio_codec").order_by("filesize").desc()
                

                for i in streams:
                    if i.filesize_approx/1000000 > 8:
                        continue
                    else:
                        i.download(filename = "file")
                        response["title"] = i.title
                        response["type"] = "mp4" if type == "video" else "webm"
                        if type == "music":
                            response = DownloadModule.convert_file(response)
                        return response
                
                raise FileTooLarge(
                                str(round(streams.last().filesize_approx/1000000, 1)) + "МБ", 
                                "8МБ")



            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()
                elif len(ctx.args) > 1:
                    if ctx.clean_args[1] != "video" and ctx.clean_args[1] != "music":
                        return CommandResult.error("Второй аргумент должен быть <video> или <music>")
                
                try:
                    response = self.download_tube(ctx.clean_args[0], ctx.clean_args[1] if len(ctx.clean_args) > 1 else "video")
                except FileTooLarge as e:
                    return CommandResult(e)
                except pytube.exceptions.LiveStreamError:
                    return CommandResult("Вы отправили ссылку на прямой эфир.")
                except pytube.exceptions.ExtractError:
                    return CommandResult("Не удалось скачать видео/аудио.")
                except pytube.exceptions.HTMLParseError:
                    return CommandResult("Не удалось проанализировать ссылку. Вероятно вы отправили ссылку не на ютуб")
                except pytube.exceptions.PytubeError:
                    return CommandResult("Неизвестная ошибка API.")
                except pytube.exceptions.VideoUnavailable:
                    return CommandResult("Данное видео недоступно. Вероятно вы отправили ссылку на заблокированное или приватное видео.")

                await ctx.message.channel.send(
                                            "Видео успешно преобразовано.\n{}\n(Заказал: {})".format(response["title"], ctx.message.author.mention), 
                                            file = discord.File("file." + response["type"]))
                
                DownloadModule.delete_file(response["type"])
                
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass

                return CommandResult.ok()
