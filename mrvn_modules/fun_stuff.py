import binascii
import json
import math
import socket

import aiohttp
import requests
from PIL import Image, ImageEnhance
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from requests import RequestException
import http.client
from decorators import mrvn_module, mrvn_command
from modular import *


class ApiError(Exception):
    text: str

    def __init__(self, text):
        self.text = text


class Huificate:
    @staticmethod
    def word(word: str, pref: str = "ху") -> str:
        if len(word) < 3:
            return word

        vowel_list = {"а": "я",
                      "о": "ё",
                      "э": "е",
                      "ы": "и",
                      "у": "ю",
                      "я": "а",
                      "ё": "о",
                      "е": "е",
                      "и": "и",
                      "ю": "у"}

        vowels = re.search(r"([аоэыуяёеию])", word)

        if vowels and len(vowels.groups()):
            vowels = vowels.groups()
            hui_word = word

            if len(vowels) >= 3 and vowels[0].lower() == vowels[1].lower():
                hui_word = word.replace(vowels[0], "")

            syllable = int(not not len(vowels) >= 3)
            diphthong = vowel_list[vowels[syllable]]

            return "%s-%s%s%s" % (word[:-1] + re.sub(r"[^А-яa-zA-Z\d\s\n]", "", word[-1]), pref, diphthong,
                                  hui_word[hui_word.index(vowels[syllable]) + 1:])
        else:
            return word

    @staticmethod
    def text(text: str) -> str:
        hui_text = []

        for word in text.split():
            hui_text.append(Huificate.word(word))

        return " ".join(hui_text)


@mrvn_module("FunStuff", "Модуль, содержащий интересные, но бесполезные команды.")
class FunStuffModule(Module):
    gay_react_words = ["галя", "гей", "gay", "galya", "cleveron", "клеверон"]
    translator_api_key = None
    translator_url = "https://translate.yandex.net/api/v1.5/tr.json/translate"

    async def on_enable(self):
        FunStuffModule.translator_api_key = os.environ.get("mrvn_translator_key")

        if FunStuffModule.translator_api_key is None:
            self.logger.error("Ключ Yandex Translator API не указан. Команда rtr не будет работать.")

        self.bot.module_handler.add_param("fun_stuff_ita_allowed_channel", 0)
        
        @mrvn_command(self, ["8ball", "8b"], "8ball", "<текст>")
        class EightBall(Command):
            response_list = ["Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да", "Можешь быть уверен в этом", "Мне кажется - да", "Вероятнее всего", "Хорошие перспективы", "Знаки говорят - да", "Да", "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать", "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять", "Даже не думай", "Мой ответ - нет", "По моим данным - нет", "Перспективы не очень хорошие", "Весьма сомнительно"]
            
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(" ".join(ctx.clean_args)) == 0:
                    return CommandResult.args_error("Вы не указали текст.")
                
                embed = ctx.get_embed(EmbedType.INFO, random.choice(self.response_list))
                embed.set_author(name="Magic 8 ball", icon_url="https://upload.wikimedia.org/wikipedia/commons/e/eb/Magic_eight_ball.png")
                
                return CommandResult.ok()

        @mrvn_command(self, ["balaboba", "blb", "yalm"], "https://yandex.ru/lab/yalm", "<текст>")
        class Yalm(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.clean_args) == 0:
                    return CommandResult.args_error()

                text = " ".join(ctx.clean_args)

                if len(text) > 9999:
                    return CommandResult.error("Превышен размер исходного текста.")

                try:
                    conn = http.client.HTTPSConnection("zeapi.yandex.net")
                    payload = json.dumps({
                        "query": text,
                        "intro": 0,
                        "filter": 1
                    })
                    headers = {
                        'Content-Type': 'application/json',
                    }
                    conn.request("POST", "/lab/api/yalm/text3", payload, headers)
                    response = conn.getresponse()
                    data = response.read()

                    if response.status != 200:
                        return CommandResult.error("Эта команда больше не работает :(")

                    response_data = json.loads(data.decode("utf-8"))

                    if response_data["bad_query"] == 1:
                        return CommandResult.error("Слишком жидкий текст. Попробуйте смягчить его.")
                    elif response_data["error"] == 1:
                        return CommandResult.error("Ошибка сервиса.")

                    fucking_embed = ctx.get_embed(EmbedType.INFO,
                                                  "**%s** %s" % (response_data["query"], response_data["text"]),
                                                  "Яндекс.Балабоба")
                    fucking_embed.color = 0xffdb4d

                    await ctx.message.channel.send(embed=fucking_embed)

                    return CommandResult.ok()
                except (http.client.HTTPException, socket.gaierror):
                    return CommandResult.error("Не удалось подключиться к серверу.")

        @mrvn_command(self, ["rtr"], "Перевести текст на рандомный или выбранный язык и обратно, что сделает его очень "
                                     "странным.",
                      "<текст>", keys_desc=["cmd=<имя команды>", "lang=<язык, 2 символа>"])
        class RtrCommand(Command):
            @staticmethod
            async def translate(text, lang):
                async with aiohttp.ClientSession(timeout=ClientTimeout(20)) as session:
                    async with session.get(FunStuffModule.translator_url,
                                           params={"key": FunStuffModule.translator_api_key, "text": text,
                                                   "lang": lang}) as response:
                        json = await response.json()

                        if json["code"] != 200:
                            raise ApiError(json["message"])

                        return " ".join(json["text"])

            async def trans_task(self, ctx, text, lang):
                try:
                    retranslated = await self.translate((await self.translate(text, lang)), "ru")
                except (asyncio.TimeoutError, aiohttp.ClientConnectionError):
                    await ctx.send_embed(EmbedType.ERROR, "Не удалось подключиться к серверу.")
                    return
                except ApiError as error:
                    await ctx.send_embed(EmbedType.ERROR, "Произошла ошибка API: %s" % error.text)
                    return

                await ctx.send_embed(EmbedType.INFO, retranslated, "Retranslate (язык: %s)" % lang)

                pass

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if FunStuffModule.translator_api_key is None:
                    return CommandResult.error(
                        "Команда не работает, так как API ключ недоступен. Возможно, бот запущен не в продакшн-среде.")

                text: str

                if "cmd" in ctx.keys:
                    command_name = ctx.keys["cmd"].lower()

                    if command_name == self.name:
                        return CommandResult.error("Так низя.")

                    command = self.module.bot.command_handler.find_command(command_name)

                    if not command:
                        return CommandResult.error("Команда не найдена.")

                    # noinspection PyBroadException
                    try:
                        result = await command.execute(ctx)
                    except Exception:
                        return CommandResult.error("При выполнении команды произошла ошибка!")

                    if not result.message:
                        return CommandResult.error("Не удалось получить сообщение от команды.")

                    text = result.message
                elif len(ctx.args) > 0:
                    text = " ".join(ctx.clean_args)
                else:
                    return CommandResult.args_error()

                if "lang" in ctx.keys:
                    lang = ctx.keys["lang"]
                else:
                    lang = random.choice(("ko", "zh", "ja", "uk", "el", "ru", "en"))

                await self.module.bot.module_handler.add_background_task(self.trans_task(ctx, text, lang), self.module)

                return CommandResult.ok(wait_emoji=True)

        @mrvn_command(self, ["tte"], "TextToEmoji - преобразовать буквы из текста в буквы-эмодзи", args_desc="<текст>")
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

        @mrvn_command(self, ["choice"], "Выбрать рандомный вариант из предоставленных", "<1, 2, 3...>")
        class ChoiceCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                choices = " ".join(ctx.clean_args).split(", ")

                if len(choices) < 2:
                    return CommandResult.args_error()

                return CommandResult.ok("Я выбираю `\"%s\"`" % random.choice(choices))

        @mrvn_command(self, ["prntscr"], "Рандомный скриншот с сервиса LightShot")
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

        @mrvn_command(self, ["joke"], "Шутник 3000!")
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

        @mrvn_command(self, ["beucode"],
                      "Компилятор текста в Беукод и обратно. Команда автоматически преобразовывает Беукод в текст или "
                      "текст в Беукод, в зависимости от того, что вы укажете.",
                      "<текст или Беукод>")
        class CommandBeucode(Command):
            @staticmethod
            def str_to_beucode(string: str):
                bits = bin(int(binascii.hexlify(string.encode("utf-8", "surrogatepass")), 16))[2:]

                return bits.zfill(8 * ((len(bits) + 7) // 8)).replace("0", "🐷").replace("1", "🐗")

            @staticmethod
            def beucode_to_str(string: str):
                bits = string.replace("🐷", "0").replace("🐗", "1")

                n = int(bits, 2)

                return n.to_bytes((n.bit_length() + 7) // 8, "big").decode("utf-8", "surrogatepass") or "\0"

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if len(ctx.clean_args) < 1:
                    return CommandResult.args_error()

                cmd_input = " ".join(ctx.clean_args)

                beucode = re.findall(r"[🐗🐷]", cmd_input)

                mode = len(beucode) > 0

                try:
                    if mode:
                        out = self.beucode_to_str(cmd_input)
                    else:
                        out = self.str_to_beucode(cmd_input)
                except (ValueError, UnicodeDecodeError):
                    return CommandResult.error("Ошибка преобразования текста.")

                return CommandResult.info(out, "Беукод (режим: %s)" % ("Beucode ➡ Text" if mode else "Text ➡ Beucode"))

        @mrvn_command(self, ["ita", "ascii"],
                      "Преобразование картинки в ASCII-арт."
                      " В случае того если размер больше 1000 в стандартном режиме, используются "
                      "альтернативные символы.",
                      "<изображение>",
                      [
                          "size=<15 - (1990 для стандартного режима, 1990*8 для брайля)> - размер арта."
                          " 750 по умолчанию для обычного режима, 8000 для брайля.",
                          "braille - режим отрисовки символами брайля",
                          "limit - допуск 0-255 (значение грейскейла,"
                          " значения больше которого будут восприниматься как белый пиксель)"
                      ])
        class ITACommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                allowed_channel_id = self.module.bot.module_handler.get_param("fun_stuff_ita_allowed_channel")

                if allowed_channel_id != 0:
                    allowed_channel = ctx.message.guild.get_channel(allowed_channel_id)

                    if allowed_channel and allowed_channel != ctx.message.channel:
                        return CommandResult.error(
                            "Вы можете выполнить эту команду только в %s" % allowed_channel.mention)

                if len(ctx.message.attachments) != 0:
                    try:
                        req = requests.get(ctx.message.attachments[0].url, allow_redirects=True)
                    except RequestException:
                        return CommandResult.error("Не удалось загрузить изображение.")
                    with open("src_image_%s.png" % ctx.message.id, "wb") as f:
                        f.write(req.content)
                    try:
                        img = Image.open("src_image_" + str(ctx.message.id) + ".png")

                    except (IOError, TypeError):
                        return CommandResult.error("В этом файле не удалось прочитать сообщение.")

                    size = 8000 if "braille" in ctx.keys else 750

                    if "size" in ctx.keys:
                        try:
                            size = max(min(1990 * 8 if "braille" in ctx.keys else 1990, int(ctx.keys["size"])), 15)
                        except ValueError:
                            return CommandResult.args_error("Укажите число.")

                    asp = math.sqrt((img.height * img.width) / size)
                    img = img.resize((int(img.size[0] / asp), int(img.size[1] / asp)), Image.ANTIALIAS)

                    img = img.convert("L")
                    img = ImageEnhance.Contrast(img).enhance(1.5)

                    if "braille" in ctx.keys:
                        """
                        У брайля анальная нумерация
                        ,___,
                        |1 4|
                        |2 5|
                        |3 6|
                        |7 8|
                        `````

                        Т.е. например если в 1 позиции будет точка и во 2 позиции будет точка, то код символа брайля
                        будет 12 (DOTS-12)
                        Но при этом еще надо под эту хуйню подобрать номер в таблице Unicode
                        Эту таблицу я спиздил, реализация моя
                        """
                        pixel_map = ((0x01, 0x08),
                                     (0x02, 0x10),
                                     (0x04, 0x20),
                                     (0x40, 0x80))

                        symbols = []
                        if "limit" in ctx.keys:
                            if ctx.keys["limit"]:
                                if 0 < int(ctx.keys["limit"]) < 255:
                                    limit = int(ctx.keys["limit"])
                                else:
                                    CommandResult.args_error("Параметр limit должен удовлетворять"
                                                             " 0 < limit < 255")
                            else:
                                CommandResult.args_error("Укажите число.")
                        else:
                            limit = 255 // 2
                        for m in range(0, img.height - 3, 4):
                            for k in range(0, img.width - 1, 2):
                                sum = 0
                                for i in range(4):
                                    for j in range(2):
                                        if img.getpixel((k + j, m + i)) > limit:
                                            sum += pixel_map[i][j]
                                symbols.append(chr(0x2800 + sum))
                        os.remove("src_image_%s.png" % ctx.message.id)
                        res = ""
                        count = 0
                        for h in range(img.height // 4):
                            for w in range(img.width // 2):
                                res += symbols[count]
                                count += 1
                            res += '\n'
                        await ctx.message.channel.send("```%s```" % res)
                    else:
                        symbols = ["░░", "░░", "▒▒", "▒▒", "▓▓", "▓▓", "██", "██"]
                        symbols_alt = ["░", "░", "▒", "▒", "▓", "▓", "█", "█"]

                        res = ""

                        for i in range(img.height):
                            for j in range(img.width):
                                pixel = img.getpixel((j, i))
                                if size <= 1000:
                                    res = res + symbols[int((pixel * 7) / 255)]
                                else:
                                    res = res + symbols_alt[int((pixel * 7) / 255)]
                            res = res + "\n"

                        os.remove("src_image_%s.png" % ctx.message.id)
                        await ctx.message.channel.send("```%s```" % res)

                        return CommandResult.ok()

                    return CommandResult.ok()
                else:
                    return CommandResult.args_error()

        @mrvn_command(self, ["huificate", "hui"], "Хуифицировать текст.", "<текст>")
        class HuificateCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                if not len(ctx.clean_args):
                    return CommandResult.args_error()

                return CommandResult.info(Huificate.text(" ".join(ctx.clean_args)), "Хуификатор")

        @mrvn_command(self, ["porngen", "pg"], "Сгенерировать случайный заголовок для порно.")
        class PornGenCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                context_list = ["Во время урока географии ",
                                "Пока муж отошел в магазин, ",
                                "Вместо фитнеса ",
                                "Перед прогулкой ",
                                "Рождественская вечеринка проходила скучно, но ",
                                "По ошибке попав на вечеринку бодибилдеров, "]
                role_list = ["незадачливый курьер и изголодавшиеся милфы ",
                             "украинская студентка со своим мускулистым парнем ",
                             "чернокожие парни и миниатюрная блондинка ",
                             "Джонни Синс и Эльза Джин "]
                adj_list = ["страстно ", "лениво ", "незатейливо ", "медленно ", "нежно ", "жёстко "]
                verb_list = ["ебались во все щели ", "трахались ", "спаривались "]
                condition_list = ["в ванной.", "в гостиной.", "на улице.", "будучи пьяными.", "пока мужа нет дома.",
                                  "пока родителей нет дома.", "слушая беубасс."]

                out = ''.join([random.choice(i) for i in [context_list,
                                                          role_list,
                                                          adj_list,
                                                          verb_list,
                                                          condition_list]])
                return CommandResult.info(out, "Генератор порно")

    async def on_event(self, event_name, *args, **kwargs):
        if event_name == "on_message":
            message: discord.Message = args[0]

            for word in self.gay_react_words:
                if word in message.content.lower():
                    await message.add_reaction("🏳️‍🌈")
        elif event_name == "on_reaction_add":
            reaction: discord.Reaction = args[0]

            if reaction.count > 2:
                await reaction.message.add_reaction(reaction)
