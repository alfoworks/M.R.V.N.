import discord

from command import CommandContext


class CommandExecutor:
    def execute(self, ctx: CommandContext):
        pass

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def is_allowed(self, message: discord.Message):
        return True