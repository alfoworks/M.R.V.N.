from typing import Optional
from command import CommandContext

import discord

class CommandResult:
    def __init__(self, embed, success, total):
        self.embed = embed
        self.success = success
        self.total = total

    @staticmethod
    def get_result(success, total):
        if success != 0:
            if total != 0:
                if success/total >= 0.5: return 0 # Больше половины успешно
                else: return 2 # Меньше половины успешно - предупреждение
            else: return 0 # Успешно
        elif total != 0: return 1 # Ошибка
        return -1

    class Builder:
        def __init__(self):
            self._embed: Optional[discord.Embed] = None
            self._success = 0
            self._total = 0

        def embed(self, embed: discord.Embed):
            self._embed = embed
            return self

        def description(self, description: str):
            if not self._embed:
                self._embed = discord.Embed()
            self._embed.description = description
            return self

        def success(self, success: int):
            self._success = success
            return self

        def total(self, total: int):
            self._total = total
            return self

        def build(self, ctx: CommandContext = None):
            if self._embed is not None:
                assert ctx is not None, "You must provide CommandContext if embed provided"
                #region Установка цвета
                res = CommandResult.get_result(self._success, self._total)
                if res is 0:
                    self._embed.colour = 0x00FF00
                elif res in (1, 2):
                    self._embed.colour = 0xFF0000
                #endregion
                #region установка подвала
                text = "Запросил: " + ctx.message.author.display_name
                if self._success > 0 and (self._success != 1 or self._total > 0):
                    text += "\nУспешно: %s" % self._success
                    if self._total > 0:
                        text += "/%s" % self._total
                self._embed.set_footer(text=text)
                #endregion Насяльника подвала построена
                self._embed.title = ctx.spec.name
            return CommandResult(self._embed, self._success, self._total)
