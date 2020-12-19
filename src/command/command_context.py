import discord
from collections import defaultdict

from command import CommandSpec


class CommandContext:
    def __init__(self, message: discord.Message, spec: CommandSpec):
        self.message = message
        self._args = defaultdict(list)
        self.spec = spec

    def put_arg(self, key, value):
        self._args[key].append(value)

    def get_one(self, key):
        if len(self._args[key]) != 1:
            return None
        return self._args[key][0]

