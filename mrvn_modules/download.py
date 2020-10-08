import os

import discord
import pytube
import requests
from pydub import AudioSegment
from pytube import YouTube

from decorators import mrvn_module, mrvn_command
from modular import Module, Command, CommandResult, CommandContext


class FileTooLarge(Exception):
    def __init__(self, required_size, size):
        self.message = "Файл слишком большой. Итоговый файл был бы в" \
                       "есом {}, когда максимальный допустимый размер {}.".format(
            size, required_size)
        super().__init__()


@mrvn_module(
    "Download",
    "Модуль для скачивания и отправки видео и аудио файлов с разых ресурсов")
class DownloadModule(Module):

    @staticmethod
    def delete_file(file_type):
        os.remove("file." + file_type)

    @staticmethod
    def convert_file(response):
        song = AudioSegment.from_file("file." + response["type"])
        song.export("file.mp3", format="mp3")
        DownloadModule.delete_file(response["type"])
        response["type"] = "mp3"
        return response

    async def on_enable(self):

        @mrvn_command(
            self,
            "coub",
            "Команда для парсинга ссылки на Coub для просмотра (или прослушки) его в Discord.",
            "<ссылка> [video/music] (video по умолчанию)")
        class CoubCommand(Command):
            @staticmethod
            def parse_link_coub(link, download_type="video"):
                link = "http://coub.com//api/v2/coubs" + link[21:]
                response = {}
                r = requests.get(link)
                s = r.json()
                response["title"] = s["title"]
                response["content"] = s["file_versions"]["html5"]["audio"]["high"][
                    "url"] if download_type == "music" else \
                    s["file_versions"]["share"]["default"]
                response["type"] = "mp3" if download_type == "music" else "mp4"
                return response

            @staticmethod
            def download_coub(response):
                res = requests.get(response["content"])
                open("file." + response["type"], "wb").write(res.content)

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()
                elif len(ctx.args) > 1:
                    if ctx.clean_args[1].lower() not in ["video", "music"]:
                        return CommandResult.error("Второй аргумент должен быть <video> или <music>")

                try:
                    response = self.parse_link_coub(ctx.clean_args[0],
                                                    ctx.clean_args[1] if len(ctx.clean_args) > 1 else "video")
                except ValueError:
                    return CommandResult.error("Указанная ссылка не работает.")
                except KeyError:
                    return CommandResult.error("Указанная ссылка не работает.")

                try:
                    self.download_coub(response)
                except requests.RequestException:
                    return CommandResult.error("Ошибка скачивания коуба.")
                except OSError:
                    return CommandResult.error("Ошибка записи коуба.")

                await ctx.message.channel.send(
                    "Коуб успешно преобразован.\n{}\n(Заказал: {})".format(response["title"],
                                                                           ctx.message.author.mention),
                    file=discord.File("file." + response["type"]))

                DownloadModule.delete_file(response["type"])

                return CommandResult.ok()

        @mrvn_command(
            self,
            "tube",
            "Команда для парсинга ссылки на YouTube для просмотра (или прослушки) его в Discord.",
            "<ссылка> [video/music] (video по умолчанию)")
        class TubeCommand(Command):

            @staticmethod
            def download_tube(link, download_type="video"):
                yt = YouTube(link)
                response = {}
                streams = yt.streams.filter(
                    only_audio=False if download_type == "video" else True,
                    file_extension="mp4" if download_type == "video" else "webm").order_by("audio_codec").order_by(
                    "filesize").desc()

                for i in streams:
                    if i.filesize_approx / 1000000 > 8:
                        continue
                    else:
                        i.download(filename="file")
                        response["title"] = i.title
                        response["type"] = "mp4" if download_type == "video" else "webm"
                        if download_type == "music":
                            response = DownloadModule.convert_file(response)
                        return response

                raise FileTooLarge(
                    str(round(streams.last().filesize_approx / 1000000, 1)) + "МБ",
                    "8МБ")

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()
                elif len(ctx.args) > 1:
                    if ctx.clean_args[1] not in ["video", "music"]:
                        return CommandResult.error("Второй аргумент должен быть <video> или <music>")

                try:
                    response = self.download_tube(ctx.clean_args[0],
                                                  ctx.clean_args[1] if len(ctx.clean_args) > 1 else "video")
                except FileTooLarge as e:
                    return CommandResult.error(e.message)
                except pytube.exceptions.LiveStreamError:
                    return CommandResult.error("Вы отправили ссылку на прямой эфир.")
                except pytube.exceptions.ExtractError:
                    return CommandResult.error("Не удалось скачать видео/аудио.")
                except pytube.exceptions.HTMLParseError:
                    return CommandResult.error(
                        "Не удалось проанализировать ссылку. Вероятно вы отправили ссылку не на ютуб.")
                except pytube.exceptions.PytubeError:
                    return CommandResult.error("Неизвестная ошибка API.")
                except pytube.exceptions.VideoUnavailable:
                    return CommandResult.error(
                        "Данное видео недоступно. Вероятно вы отправили ссылку на заблокированное или приватное видео.")

                await ctx.message.channel.send(
                    "Видео успешно преобразовано.\n{}\n(Заказал: {})".format(response["title"],
                                                                             ctx.message.author.mention),
                    file=discord.File("file." + response["type"]))

                DownloadModule.delete_file(response["type"])

                return CommandResult.ok()
