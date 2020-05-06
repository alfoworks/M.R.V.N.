import asyncio
import time

import discord

from decorators import mrvn_module
from modular import Module, LanguageUtils


@mrvn_module("BotStatus", "Установка статуса бота, отображение аптайма в нём.")
class BotStatusModule(Module):
    async def status_update_task(self):
        custom_text = False

        while True:
            status = self.bot.module_handler.get_param(
                "bot_status_custom_text") if custom_text else "🕒 Аптайм: %s" % LanguageUtils.formatted_duration(
                time.time() - self.bot.start_time)
            await self.bot.change_presence(status=discord.Status.idle,
                                           activity=discord.Activity(
                                               name=status,
                                               type=discord.ActivityType.listening))

            custom_text = not custom_text

            await asyncio.sleep(60)

    async def on_enable(self):
        self.bot.module_handler.add_param("bot_status_custom_text", "🐖 Беубасс")

        self.logger.info("Запуск таска обновления статуса...")

        await self.bot.module_handler.add_background_task(self.status_update_task(), self)
