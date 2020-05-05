import asyncio
import time

import discord

from decorators import mrvn_module
from modular import Module, LanguageUtils


@mrvn_module("BotStatus", "Установка статуса бота, отображение аптайма в нём.")
class BotStatusModule(Module):
    async def status_update_task(self):
        beu = False

        while True:
            status = "🐖 Беубасс" if beu else "🕒 Аптайм: %s" % LanguageUtils.formatted_duration(
                time.time() - self.bot.start_time)
            await self.bot.change_presence(status=discord.Status.idle,
                                           activity=discord.Activity(
                                               name=status,
                                               type=discord.ActivityType.listening))

            beu = not beu

            await asyncio.sleep(60)

    async def on_enable(self):
        self.logger.info("Запуск таска обновления статуса...")

        await self.bot.module_handler.add_background_task(self.status_update_task(), self)
