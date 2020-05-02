import asyncio
import time

import discord

from decorators import mrvn_module
from modular import Module


@mrvn_module("BotStatus", "Установка статуса бота, отображение аптайма в нём.")
class BotStatusModule(Module):
    async def status_update_task(self):
        while True:
            uptime = time.time() - self.bot.start_time

            await self.bot.change_presence(status=discord.Status.idle,
                                           activity=discord.Activity(
                                               # name="🆙 Аптайм: %s" % LanguageUtils.formatted_duration(uptime),
                                               name="🐖 Беубасс",
                                               type=discord.ActivityType.listening))

            await asyncio.sleep(15)

    async def on_enable(self):
        self.logger.info("Запуск таска обновления статуса...")

        await self.bot.module_handler.add_background_task(self.status_update_task(), self)
