import asyncio
import inspect
import json
import os
import time
import traceback
import zlib
from typing import Dict

import aiohttp
import discord
import requests

import modular
from mrvn_config import MrvnConfig

logger = modular.Logger("Main")


class MrvnModuleHandler(modular.ModuleHandler):
    def load_modules(self):
        for modules_dir in MrvnConfig.modules_dirs:
            for file in os.listdir(modules_dir):
                should_load = file not in MrvnConfig.ignored_modules

                if file.endswith(".py") and should_load:
                    if file != "base.py":
                        continue

                    try:
                        module_file = __import__("%s.%s" % (modules_dir, file[:-3]), globals(), locals(),
                                                 fromlist=["py"])
                    except Exception:
                        logger.error("Не удалось загрузить файл %s:\n%s" % (file, traceback.format_exc()))
                        continue

                    classes = inspect.getmembers(module_file, inspect.isclass)

                    if len(classes) == 0:
                        logger.error("Не удалось загрузить файл %s. Файл не содержит классов." % file)
                        continue

                    loaded = False

                    for cls in classes:
                        if cls[1] != modular.Module and issubclass(cls[1], modular.Module):
                            module = cls[1](bot)
                            self.load_module(module)
                            loaded = True

                            logger.info("Загружен модуль %s" % module.name)

                            break

                    if not loaded:
                        logger.error("Не удалось загрузить файл %s. Файл не содержит класса модуля." % file)


bot = modular.Bot("M.R.V.N.", MrvnModuleHandler(),
                  modular.CommandHandler(modular.PrefixContextGenerator("!"), MrvnConfig.guild_whitelist),
                  time.time())

logger.info("Загрузка модулей...")
bot.module_handler.load_modules()

logger.info("Вход в Discord...")

d = zlib.decompressobj()


@bot.event
async def on_socket_raw_receive(msg):
    if type(msg) is bytes:
        buf = bytearray()
        buf.extend(msg)

        if len(msg) >= 4:
            if msg[-4:] == b'\x00\x00\xff\xff':
                msg = d.decompress(buf)
                msg = msg.decode('utf-8')
            else:
                return
        else:
            return
    else:
        return

    response = json.loads(msg)

    if response["t"] != "INTERACTION_CREATE":
        return

    cmd = response["d"]["data"]["name"]
    channel: discord.TextChannel = bot.get_channel(int(response["d"]["channel_id"]))

    for command in list(bot.command_handler.commands.values()):
        if command.name == cmd:
            url = "https://discord.com/api/v8/interactions/%s/%s/callback" % (
                response["d"]["id"], response["d"]["token"])

            interaction_response = {
                "type": 4,
                "data": {
                    "content": "Congrats on sending your command!"
                }
            }
            r = requests.post(url, json=interaction_response)

            logger.info("[SLASH-COMMAND] {%s/#%s} Выполнена команда %s" % (
                response["d"]["member"]["nick"], channel, cmd))

            message = await channel.fetch_message(channel.last_message_id)

            content = "!%s" % cmd

            message.content = content

            await bot.command_handler.handle(message)

            break


async def register_slash_command(slash_command: Dict, guild_id: int = None):
    url = "https://discord.com/api/v8/applications/%s" % bot.user.id
    url += "/commands" if not guild_id else "/guilds/%s/commands" % guild_id

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers={"Authorization": "Bot %s" % MrvnConfig.get_token()}, json=slash_command) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await register_slash_command(slash_command, guild_id)
            if not 200 <= resp.status < 300:
                # raise RequestFailure(resp.status, await resp.text())
                logger.error("Error registering slash command %s: %s %s" % (slash_command, resp.status, await resp.text()))
            return await resp.json()


async def delete_slash_command(slash_command_id: int, guild_id: int = None):
    url = "https://discord.com/api/v8/applications/%s" % bot.user.id
    url += "/commands" if not guild_id else "/guilds/%s/commands" % guild_id
    url += "/%s" % slash_command_id

    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers={"Authorization": "Bot %s" % MrvnConfig.get_token()}) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                await delete_slash_command(slash_command_id, guild_id)
            if not 200 <= resp.status < 300:
                # raise RequestFailure(resp.status, await resp.text())
                logger.error("Error deleting slash command %s: %s %s" % (slash_command_id, resp.status, await resp.text()))


async def get_slash_commands(guild_id: int = None):
    url = "https://discord.com/api/v8/applications/%s" % bot.user.id
    url += "/commands" if not guild_id else "/guilds/%s/commands" % guild_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"Authorization": "Bot %s" % MrvnConfig.get_token()}) as resp:
            if resp.status == 429:
                _json = await resp.json()
                await asyncio.sleep(_json["retry_after"])
                return await get_slash_commands(guild_id)
            if not 200 <= resp.status < 300:
                # raise RequestFailure(resp.status, await resp.text())
                logger.error("Error getting slash commands: %s %s" % (resp.status, await resp.text()))
            return await resp.json()


@bot.event
async def on_ready():
    logger.info("Вход выполнен от %s" % bot.user)

    logger.info("Загрузка параметров...")

    bot.module_handler.load_params()

    logger.info("Включение модулей...")

    for module in bot.module_handler.modules:
        try:
            await module.on_enable()
        except Exception:
            logger.error("Не удалось включить модуль %s!\n%s" % (module.name, traceback.format_exc()))

    logger.info("Очистка слеш-команд")

    registered_slash_commands = await get_slash_commands(394132321839874050)

    for slash_command in registered_slash_commands:
        await delete_slash_command(slash_command["id"], 394132321839874050)

    await asyncio.sleep(3)

    logger.info("Добавление слеш-команд...")

    for command in list(bot.command_handler.commands.values()):
        slash_command = command.get_slash_command()

        await register_slash_command(slash_command, 394132321839874050)

        logger.ok("Слеш-команда %s добавлена!" % slash_command["name"])

    logger.ok("===============")

    logger.ok("Загрузка завершена за %.2f сек." % (time.time() - bot.start_time))
    logger.ok("Загружено Модулей: %s" % len(bot.module_handler.modules))
    logger.ok("Загружено Команд: %s" % len(bot.command_handler.commands))

    logger.ok("===============")


@bot.event
async def on_message(message: discord.Message):
    await bot.command_handler.handle(message)


bot.run(MrvnConfig.get_token())
