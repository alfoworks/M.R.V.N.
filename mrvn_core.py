#  The MIT License (MIT)
#
#  Copyright © «2020» «ALFO:WorkS, Iterator»
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import inspect
import os
import time

import discord

import modular
from mrvn_config import MrvnConfig

logger = modular.Logger("Main")


class MrvnModuleHandler(modular.ModuleHandler):
    def load_modules(self):
        for file in os.listdir(MrvnConfig.modules_dir):
            if file.endswith(".py"):
                module_file = __import__("%s.%s" % (MrvnConfig.modules_dir, file[:-3]), globals(), locals(),
                                         fromlist=["py"])

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
                  modular.CommandHandler(modular.PrefixContextGenerator("?"), MrvnConfig.guild_whitelist),
                  time.time())

logger.info("Загрузка модулей...")
bot.module_handler.load_modules()

logger.info("Вход в Discord...")


@bot.event
async def on_ready():
    logger.info("Вход выполнен от %s" % bot.user)

    logger.info("Загрузка параметров...")

    bot.module_handler.load_params()

    logger.info("Включение модулей...")

    for module in bot.module_handler.modules:
        await module.on_enable()

    logger.ok("===============")

    logger.ok("Загрузка завершена за %.2f сек." % (time.time() - bot.start_time))
    logger.ok("Загружено Модулей: %s" % len(bot.module_handler.modules))
    logger.ok("Загружено Команд: %s" % len(bot.command_handler.commands))

    logger.ok("===============")


@bot.event
async def on_message(message: discord.Message):
    await bot.command_handler.handle(message)


bot.run(MrvnConfig.get_token())
