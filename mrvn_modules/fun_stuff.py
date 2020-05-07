import aiohttp
import requests
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from decorators import mrvn_module, mrvn_command
from modular import *


@mrvn_module("FunStuff", "Модуль, содержащий интересные, но бесполезные команды.")
class FunStuffModule(Module):
    gay_react_words = ["галя", "гей", "gay", "galya", "cleveron", "клеверон"]
    translator_api_key = None
    translator_url = "https://translate.yandex.net/api/v1.5/tr.json/translate"

    async def on_enable(self):
        FunStuffModule.translator_api_key = os.environ.get("mrvn_translator_key")

        if FunStuffModule.translator_api_key is None:
            self.logger.error("Ключ Yandex Translator API не указан. Команда rtr не будет работать.")

        @mrvn_command(self, "rtr", "Перевести текст на китайский и обратно, что сделает его очень странным.",
                      "<текст>")
        class RtrCommand(Command):
            @staticmethod
            async def translate(text, lang):
                async with aiohttp.ClientSession(timeout=ClientTimeout(20)) as session:
                    async with session.get(FunStuffModule.translator_url,
                                           params={"key": FunStuffModule.translator_api_key, "text": text,
                                                   "lang": lang}) as response:
                        return " ".join((await response.json())["text"])

            async def trans_task(self, ctx):
                try:
                    retranslated = await self.translate(
                        (await self.translate((await self.translate(" ".join(ctx.clean_args), "zh")), "ja")), "ru")
                except (asyncio.TimeoutError, aiohttp.ClientConnectionError):
                    await ctx.send_embed(EmbedType.ERROR, "Не удалось подключиться к серверу.")
                    return

                await ctx.send_embed(EmbedType.INFO, retranslated, "Retranslate")

                pass

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if FunStuffModule.translator_api_key is None:
                    return CommandResult.error(
                        "Команда не работает, так как API ключ недоступен. Возможно, бот запущен не в продакшн-среде.")

                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                await self.module.bot.module_handler.add_background_task(self.trans_task(ctx), self.module)

                return CommandResult.ok(wait_emoji=True)

        @mrvn_command(self, "tte", "TextToEmoji - преобразовать буквы из текста в буквы-эмодзи", args_desc="<текст>")
        class TTECommand(Command):
            emojiDict = {"a": "🇦", "b": "🇧", "c": "🇨", "d": "🇩", "e": "🇪", "f": "🇫", "g": "🇬", "h": "🇭",
                         "i": "🇮",
                         "j": "🇯", "k": "🇰", "l": "🇱", "m": "🇲", "n": "🇳", "o": "🇴", "p": "🇵", "q": "🇶",
                         "r": "🇷",
                         "s": "🇸", "t": "🇹", "u": "🇺", "v": "🇻", "w": "🇼", "x": "🇽", "y": "🇾", "z": "🇿",
                         "0": "0⃣",
                         "1": "1⃣ ",
                         "2": "2⃣ ", "3": "3⃣ ", "4": "4⃣ ", "5": "5⃣ ", "6": "6⃣ ", "7": "7⃣ ", "8": "8⃣ ", "9": "9⃣ ",
                         "?": "❔",
                         "!": "❕", " ": "    ", "-": "➖"}

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.args) < 1:
                    return CommandResult.args_error()

                string = ""
                for char in " ".join(ctx.clean_args).strip().lower():
                    string += self.emojiDict[char] + " " if char in self.emojiDict else char + " "

                await ctx.message.channel.send(string)

                return CommandResult.ok()

        @mrvn_command(self, "choice", "Выбрать рандомный вариант из предоставленных", "<1, 2, 3...>")
        class ChoiceCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                choices = " ".join(ctx.clean_args).split(", ")

                if len(choices) < 2:
                    return CommandResult.args_error()

                return CommandResult.ok("Я выбираю `\"%s\"`" % random.choice(choices))

        @mrvn_command(self, "prntscr", "Рандомный скриншот с сервиса LightShot")
        class PrntScrCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                chars = "abcdefghijklmnopqrstuvwxyz1234567890"
                res = None

                max_attempts = 15

                for _ in range(max_attempts):
                    code = ""

                    for i in range(5):
                        code += chars[random.randint(1, len(chars)) - 1]

                    url = "https://prnt.sc/" + code

                    html_doc = requests.get(url,
                                            headers={"user-agent": "Mozilla/5.0 (iPad; U; CPU "
                                                                   "OS 3_2 like Mac OS X; "
                                                                   "en-us) "
                                                                   "AppleWebKit/531.21.10 ("
                                                                   "KHTML, like Gecko) "
                                                                   "Version/4.0.4 "
                                                                   "Mobile/7B334b "
                                                                   "Safari/531.21.102011-10-16 20:23:10"}).text
                    soup = BeautifulSoup(html_doc, "html.parser")

                    if not soup.find_all("img")[0]["src"].startswith("//st.prntscr.com"):
                        res = soup.find_all("img")[0]["src"]
                        break

                if not res:
                    return CommandResult.error(
                        "Превышено кол-во попыток поиска изображения (%s)" % max_attempts)

                embed: discord.Embed = ctx.get_embed(EmbedType.INFO, "", "Рандомное изображение с LightShot")
                embed.set_image(url=res)

                await ctx.message.channel.send(embed=embed)

                return CommandResult.ok()

        @mrvn_command(self, "joke", "Шутник 3000")
        class CommandJoke(Command):
            phrases = ["ыыы ёпта бля", "писос", "вот это прикол", "короче", "иду я такой", "а он", "ахуеть можно",
                       "ваще",
                       "ну ты пиздец", "пацан", "подумал я", "сюда иди", "а я ему", "как будто",
                       "на нахуй!", "и после этого", "откуда ни возьмись", "Нойра пидор", "около падика",
                       "обмазался говном",
                       "отъебись", "ээээ", "ну и тут я охуел", "писос бомбит", "я тебя срамаю", "на новый год",
                       "го ПВП или зассал?!", "Джигурда", "Кристина - шлюха", "ведь так я и знал", "от этого",
                       "да ты охуел", "а ты в курсе, что", "у Пивасера хуй в суперпозиции", "и вижу Аксель Нойру ебёт",
                       "заебись!", "я и подумал, что", "пизда рулю", "да я тебя на ноль умножу", "твоя мамка",
                       "ебал в рот",
                       "пальцем в жопе", "член сосёт", "ебёт в пердак", "пидор!", "кек", "какого хуя?!", "Сэвич алкаш",
                       "письку дрочит", "оказывается", "ёбаный в рот!!", "дверь мне запили!", "на вокзале",
                       "всю хату заблевал", "обосрался", "за углом", "думаю что", "у Халаута", "ну нахуй!", "нахуй",
                       "в суперпозиции", "на хате", "два часа", "в семь утра", "урааа!!", "я снимаю нахуй!",
                       "охуевший Гликнот",
                       "клитор лижет", "всё хуйня...", "ку ку ёпта!", "хату разгриферил", "заебался я за сегодня",
                       "в последний раз",
                       "да и хуй с ним...", "сука", "богохульник ебаный", "кончил на лицо", "твою мамку",
                       "подрочу пожалуй",
                       "кто бы мог подумать", "ты не поверишь, но", "ХХЫЫЫЫ...", "то чувство, когда",
                       "неделю не просыхал", "беу", "жидко-ватто", "беубасс", "ой-ой-ой....", "40 лет как под наркозом,"
                                                                                              "еби меня, еби!",
                       "дрочи мой хуй себе в рот", "я знаю, ты любишь отсасывать!",
                       "дрочи мои соски и еби меня", "♂300 bucks♂", "♂fucking slave♂", "♂stick finger in my ass♂",
                       "♂semen♂", "♂fisting♂", "задеанонил данбонуса", "поебался", "на фонтанку", "в колпино",
                       "моя жадная пизда хочет твой хуй"]

            async def execute(self, ctx: CommandContext) -> CommandResult:
                out = ""

                for i in range(random.randint(1, 16)):
                    out += random.choice(self.phrases) + " "

                return CommandResult.info(out, "Шутник 3000")

    async def on_event(self, event_name, *args, **kwargs):
        if event_name != "on_message":
            return

        message: discord.Message = args[0]

        for word in self.gay_react_words:
            if word in message.content.lower():
                await message.add_reaction("🏳️‍🌈")
