import asyncio
import datetime
import difflib
import os
import pickle
import random
import re
import traceback
from enum import Enum
from typing import List, Coroutine, Dict, Union

import discord
from discord.embeds import EmptyEmbed

key_regex = re.compile(r"--([^\s=]+)(?:=(\S+))?")


class LanguageUtils:
    @staticmethod
    def pluralize(number: int, nom_sing: str, gen_sing: str, gen_pl: str) -> str:
        s_last_digit = str(number)[-1]

        pluralized: str

        if int(str(number)[-2:]) in range(11, 20):
            # 11-19
            pluralized = gen_pl
        elif s_last_digit == '1':
            # 1
            pluralized = nom_sing
        elif int(s_last_digit) in range(2, 5):
            # 2,3,4
            pluralized = gen_sing
        else:
            # 5,6,7,8,9,0
            pluralized = gen_pl

        return "%s %s" % (number, pluralized)

    @staticmethod
    def formatted_duration(secs: int, format_to: int = 2) -> str:
        days = round(secs // 86400)
        hours = round((secs - days * 86400) // 3600)
        minutes = round((secs - days * 86400 - hours * 3600) // 60)
        seconds = round(secs - days * 86400 - hours * 3600 - minutes * 60)

        days_text = LanguageUtils.pluralize(days, "день", "дня", "дней")
        hours_text = LanguageUtils.pluralize(hours, "час", "часа", "часов")
        minutes_text = LanguageUtils.pluralize(minutes, "минута", "минуты", "минут")
        seconds_text = LanguageUtils.pluralize(seconds, "секунда", "секунды", "секунд")

        formatted = ", ".join(filter(lambda x: bool(x), [days_text if days else "",
                                                         hours_text if hours and format_to == 0 else "",
                                                         minutes_text if minutes and format_to > 0 else "",
                                                         seconds_text if seconds and format_to > 1 else ""]))

        return formatted


class Logger:
    name: str

    class Colors(Enum):
        BLUE = "\033[94m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        ENDC = "\033[0m"
        GREEN = '\033[92m'

    def __init__(self, name: str):
        self.name = name

    def log(self, message: str, message_type: str, color: str):
        print("%s[%s] [%s\\%s]: %s%s" % (color,
                                         datetime.datetime.now().strftime("%d.%m.%G %H:%M:%S.%f")[:-3], self.name,
                                         message_type, message,
                                         self.Colors.ENDC.value))

    def info(self, message: str):
        self.log(message, "INFO", self.Colors.BLUE.value)

    def warn(self, message: str):
        self.log(message, "WARN", self.Colors.YELLOW.value)

    def error(self, message: str):
        self.log(message, "ERROR", self.Colors.RED.value)

    def ok(self, message: str):
        self.log(message, "OK", self.Colors.GREEN.value)


class Module:
    name: str
    description: str
    bot = None
    logger: Logger
    tasks = []

    def __init__(self, bot):
        self.bot = bot
        self.tasks = []

    async def on_enable(self):
        pass

    async def on_event(self, event_name, *args, **kwargs):
        pass


class ModuleHandler:
    modules: List[Module] = []
    logger: Logger
    params_file = "./params.pkl"
    params = {}

    def __init__(self):
        self.logger = Logger("ModuleHandler")

    def load_modules(self):
        pass

    def load_module(self, module: Module):
        self.modules.append(module)

    def unload_module(self, module: Module):
        for task in list(module.tasks):
            task.cancel()
            module.tasks.remove(task)

            self.logger.info("Отменён таск модуля %s" % module.name)

        self.modules.remove(module)

        self.logger.info("Отгружен модуль %s" % module.name)

    async def __wait_for_task_to_end(self, module, task):
        await task

        if task in module.tasks:
            module.tasks.remove(task)

    async def add_background_task(self, coro: Coroutine, module: Module):
        task = asyncio.ensure_future(coro)

        module.tasks.append(task)

        asyncio.ensure_future(self.__wait_for_task_to_end(module, task))

    def add_param(self, key: str, value_default):
        if key not in self.params:
            self.set_param(key, value_default, True)

    def set_param(self, key: str, value, save=False):
        self.params[key] = value

        if save:
            self.save_params()

    def get_param(self, key: str):
        return self.params[key]

    def save_params(self):
        with open(self.params_file, "wb") as f:
            pickle.dump(self.params, f)

    def load_params(self):
        if not os.path.isfile(self.params_file):
            self.save_params()
        else:
            with open(self.params_file, "rb") as f:
                self.params = pickle.load(f)


class PermissionHandler:
    def has_permission(self, member: discord.Member) -> bool:
        pass


class AcceptAllPermissionHandler(PermissionHandler):
    def has_permission(self, member: discord.Member) -> bool:
        return True


class DiscordPermissionHandler(PermissionHandler):
    permissions: List[str]

    def __init__(self, permissions: List[str]):
        self.permissions = permissions

    def has_permission(self, member: discord.Member) -> bool:
        for k, v in iter(member.guild_permissions):
            if k in self.permissions and not v:
                return False

        return True


class UserWhitelistPermissionHandler(PermissionHandler):
    user_ids: List[int]

    def __init__(self, user_ids: List[int]):
        self.user_ids = user_ids

    def has_permission(self, member: discord.Member) -> bool:
        return member.id in self.user_ids


class EmbedType(Enum):
    OK = (discord.colour.Color.green(), "ОК")
    INFO = (0, "Инфо")
    ERROR = (discord.colour.Color.red(), "Ошибка")


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

            return "%s-%s%s%s" % (word[:-1] + re.sub(r"[^А-яa-zA-Z\d\s:]", "", word[-1]), pref, diphthong,
                                  hui_word[hui_word.index(vowels[syllable]) + 1:])
        else:
            return word

    @staticmethod
    def text(text: str) -> str:
        hui_text = []

        for word in text.split():
            hui_text.append(Huificate.word(word))

        return " ".join(hui_text)


class CustomEmbed(discord.Embed):
    def add_field(self, *, name, value, inline=True):
        super().add_field(name=Huificate.text(name), value=Huificate.text(value), inline=inline)

    def set_author(self, *, name, url=EmptyEmbed, icon_url=EmptyEmbed):
        super().set_author(name=Huificate.text(name), url=url, icon_url=url)


class CommandContext:
    message: discord.Message
    abstract_content: str
    command_str: str
    args: List[str]
    clean_args: List[str]
    raw_keys: List[str]
    keys: Dict[str, Union[str, bool]]

    message_limit = 2048
    too_big_message = "***Размер сообщение был превышен и обрезан до %s символов***" % message_limit

    def __init__(self, message: discord.Message, command_str: str, args: List[str], clean_args: List[str],
                 raw_keys: List[str], keys: Dict[str, Union[str, bool]], abstract_content: str):
        self.message = message
        self.args = args
        self.clean_args = clean_args
        self.raw_keys = raw_keys
        self.keys = keys
        self.command_str = command_str
        self.abstract_content = abstract_content

    @staticmethod
    def limit_message(message: str):
        if len(message) <= 2048:
            return message

        limited = ("%s\n%s" % (CommandContext.too_big_message, message))[:2048]

        return limited

    def get_custom_embed(self, message: str, title: str, color: int, sign: bool = True) -> discord.Embed:
        embed = CustomEmbed(color=color, description=self.limit_message(
            Huificate.text(message)) if message is not None else None,
                            title="**%s**" % Huificate.text(title))

        if sign:
            embed.set_footer(icon_url=self.message.author.avatar_url,
                             text=Huificate.text("Запросил: %s" % "%s#%s" % (
                                 self.message.author.display_name, self.message.author.discriminator)))

            embed.timestamp = self.message.created_at

        return embed

    @staticmethod
    def get_custom_embed_static(message: str, title: str, color: int) -> discord.Embed:
        embed = CustomEmbed(color=color,
                            description=CommandContext.limit_message(
                                Huificate.text(message)) if message is not None else None,
                            title="**%s**" % Huificate.text(title))

        return embed

    def get_embed(self, embed_type: EmbedType, message: str, title: str = None, sign: bool = True):
        color = self.message.guild.me.top_role.color if embed_type == EmbedType.INFO else embed_type.value[0]

        return self.get_custom_embed(message, embed_type.value[1] if title is None else title, color, sign)

    async def send_embed(self, embed_type: EmbedType, message: str, title: str = None,
                         channel_to_send: discord.TextChannel = None, sign: bool = True):
        channel = self.message.channel if channel_to_send is None else channel_to_send

        await channel.send(embed=self.get_embed(embed_type, message, title, sign=sign))

    async def send(self, message: str, reply: bool = False, channel_to_send: discord.TextChannel = None):
        message = self.limit_message(message)

        channel = self.message.channel if channel_to_send is None else channel_to_send

        await channel.send(("%s, %s" % (self.message.author.mention, message)) if reply else message)


class ContextGenerator:
    def process_message(self, message: discord.Message) -> CommandContext:
        pass


class PrefixContextGenerator(ContextGenerator):
    prefix: str

    def __init__(self, prefix: str):
        self.prefix = prefix

    def process_message(self, message: discord.Message):
        if not message.content.startswith(self.prefix):
            return None

        args: list = message.content.split()
        clean_args = message.clean_content.split()[1:]
        command = args.pop(0)[len(self.prefix):].lower()

        raw_keys = []
        keys = {}
        for arg in list(args):
            arg: str
            matcher = key_regex.fullmatch(arg)
            if matcher is not None:
                keys[matcher.group(1)] = matcher.group(2) is None or matcher.group(2)
                clean_args.remove(matcher.group(0))
                args.remove(matcher.group(0))

        return CommandContext(message, command, args, clean_args, raw_keys, keys, message.content[len(self.prefix):])


class CommandResult:
    error: bool
    args_error: bool
    access_denied: bool
    embed_type: EmbedType
    message: str
    title: str
    color: int
    wait_emoji: bool

    def __init__(self, error: bool, message: str, embed_type: EmbedType, title: str = None, color: int = None,
                 args_error: bool = False, access_denied: bool = False, wait_emoji=False):
        self.error = error
        self.message = message
        self.title = title
        self.color = color
        self.embed_type = embed_type
        self.args_error = args_error
        self.access_denied = access_denied
        self.wait_emoji = wait_emoji

    @staticmethod
    def ok(message: str = None, title: str = None, color: int = None, wait_emoji=False):
        return CommandResult(False, message, EmbedType.OK, title, color, wait_emoji=wait_emoji)

    @staticmethod
    def info(message: str = None, title: str = None, color: int = None):
        return CommandResult(False, message, EmbedType.INFO, title, color)

    @staticmethod
    def error(message: str = None, title: str = None, color: int = None):
        return CommandResult(True, message, EmbedType.ERROR, title, color)

    @staticmethod
    def args_error(message: str = None):
        return CommandResult(True, message, EmbedType.ERROR, "Недостаточно аргументов!", args_error=True)

    @staticmethod
    def access_denied():
        return CommandResult(True, "", embed_type=EmbedType.ERROR, access_denied=True)


class Command:
    name: str
    description: str
    args_description: str
    keys_description: List[str]
    perm_handler: PermissionHandler
    module: Module
    should_await: bool

    def __init__(self, name: str, description: str, args_description: str = "", keys_description=None,
                 perm_handler: PermissionHandler = None, module: Module = None, should_await: bool = True):
        if keys_description is None:
            keys_description = []

        if perm_handler is None:
            perm_handler = AcceptAllPermissionHandler()

        self.name = name
        self.description = description
        self.args_description = args_description
        self.keys_description = keys_description
        self.perm_handler = perm_handler
        self.module = module
        self.should_await = should_await

    async def execute(self, ctx: CommandContext) -> CommandResult:
        pass

    def get_detailed_name(self) -> str:
        name = self.name

        if len(self.args_description):
            name += " %s" % self.args_description

        if len(self.keys_description):
            name += " [%s]" % "/".join(self.keys_description)

        return name


class CommandListener:
    module: Module

    def __init__(self, module: Module):
        self.module = module

    async def on_command_execute(self, command: Command, result: CommandResult, ctx: CommandContext):
        pass

    async def on_command_pre_execute(self, command: Command, ctx: CommandContext) -> bool:
        return True


class CommandHandler:
    emojis = {
        "ok": "☑",
        "error": "❌",
        "access_denied": "🚫",
        "args_error": "⁉",
        "wait": "⏳"
    }

    access_denied_messages = ["Нет прав!", "Прав не завезли.", "Вы точно уверены? (да/нет)", "Что-то пошло не так. "
                                                                                             "Попробуйте позже",
                              "Увы, но ты слишком мелковат для этого действия.",
                              "Действие НЕ выполнено. Не знаю, почему.",
                              "[ACCESS DENIED!](https://www.youtube.com/watch?v=2dZy3cd9KFY)"]

    commands: Dict[str, Command]
    command_listeners: Dict[str, CommandListener]
    context_generator: ContextGenerator
    whitelist: List[int]
    logger: Logger

    def __init__(self, context_generator: ContextGenerator, whitelist: List[int]):
        self.context_generator = context_generator
        self.whitelist = whitelist
        self.logger = Logger('CommandHandler')

        self.commands = {}
        self.command_listeners = {}
        self.whitelist = whitelist

    async def handle(self, message: discord.Message):
        context = self.context_generator.process_message(message)

        if not context or not isinstance(message.author, discord.Member) or len(
                message.content) < 2 or message.author is message.guild.me:
            return

        result: CommandResult
        emoji = None
        command = None

        if message.guild.id not in self.whitelist:
            result = CommandResult.error("Этот сервер не состоит в белом списке разрешенных серверов бота.")
        elif context.command_str not in self.commands:
            similar_commands = []

            for command in list(self.commands.values()):
                ratio = difflib.SequenceMatcher(None, context.command_str, command.name).ratio()

                if ratio > 0.5:
                    similar_commands.append("%s" % command.name)

            result = CommandResult.error("Ты %s\n%s" % (
                context.abstract_content,
                ("Возможно, вы имели в виду: %s" % ", ".join(similar_commands)) if len(
                    similar_commands) else ""),
                                         "Команда не найдена!")
        else:
            command = self.commands[context.command_str]

            if not command.perm_handler.has_permission(message.author):
                result = CommandResult.error(random.choice(self.access_denied_messages), "Нет прав!")
                emoji = self.emojis["access_denied"]
            else:
                should_execute = True

                for listener in list(self.command_listeners.values()):
                    should_execute = await listener.on_command_pre_execute(command, context) is True and should_execute

                if not should_execute:
                    return

                if command.should_await:
                    # noinspection PyBroadException
                    try:
                        result = await command.execute(context)
                    except discord.Forbidden:
                        result = CommandResult.error("У бота нет прав, чтобы совершить это действие!")
                    except Exception:
                        result = CommandResult.error(
                            "Техническая информация/Stacktrace: ```%s```" % traceback.format_exc(limit=10),
                            "⚠ Не удалось выполнить команду ⚠")

                    if result.access_denied:
                        result = CommandResult.error(random.choice(self.access_denied_messages), "Нет прав!")
                        emoji = self.emojis["access_denied"]
                    elif result.wait_emoji:
                        emoji = self.emojis["wait"]
                else:
                    asyncio.ensure_future(command.execute(context))
                    result = CommandResult.ok()
                    emoji = self.emojis["wait"]

                for listener in list(self.command_listeners.values()):
                    asyncio.ensure_future(listener.on_command_execute(command, result, context))

        embed = context.get_embed(result.embed_type, result.message, result.title)

        if result.args_error and command:
            emoji = self.emojis["args_error"]

            embed.add_field(
                name=command.get_detailed_name(),
                value=command.description, inline=False)

        if result.title is not None or result.message is not None:
            await message.channel.send(embed=embed)

        try:
            await message.add_reaction(emoji if emoji else self.emojis["error"] if result.error else self.emojis["ok"])
        except discord.NotFound:
            pass

    def register_command(self, command: Command):
        self.commands[command.name] = command

    def unregister_command(self, command: Command):
        del self.commands[command.name]

        self.logger.info("Отгружена команда %s модуля %s" % (command.name, command.module.name))

    def register_listener(self, listener: CommandListener):
        self.command_listeners[listener.module.name] = listener

    def unregister_module_commands(self, module_name: str):
        for command in list(self.commands.values()):
            if command.module.name == module_name:
                self.unregister_command(command)

        if module_name in self.command_listeners:
            del self.command_listeners[module_name]


class Bot(discord.Client):
    name = ""

    module_handler: ModuleHandler
    command_handler: CommandHandler

    logger: Logger

    start_time: float

    def __init__(self, name: str, module_handler: ModuleHandler,
                 command_handler: CommandHandler, start_time: float):
        super().__init__()

        self.name = name
        self.module_handler = module_handler
        self.command_handler = command_handler
        self.start_time = start_time

        self.logger = Logger(self.name)

    async def run_modules_event(self, event_name, *args, **kwargs):
        for module in self.module_handler.modules:
            try:
                await module.on_event(event_name, *args, **kwargs)
            except Exception:
                self.logger.error(
                    "Ошибка при выполнении ивента %s модулем %s:\n%s" % (
                        event_name, module.name, traceback.format_exc()))

    def dispatch(self, event, *args, **kwargs):
        method = 'on_' + event

        super().dispatch(event, *args, **kwargs)

        asyncio.ensure_future(self.run_modules_event(method, *args, **kwargs))
