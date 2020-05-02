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
