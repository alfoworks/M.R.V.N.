#  The MIT License (MIT)
#
#  Copyright © «2020» «ALFO:WorkS, Iterator»
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
