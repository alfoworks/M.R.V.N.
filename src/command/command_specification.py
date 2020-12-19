import discord

from command import CommandExecutor
from command.command_context import CommandContext


class CommandSpec:
    def __init__(self, cls: CommandExecutor, *aliases, name="" , description="", arguments=None):
        self.cls = cls
        self._module = None
        self.aliases = aliases
        self.arguments = arguments or []
        self.description = description
        self.name = name
        self.subcommands = []
        for subcommand in filter(lambda x: x is CommandSpec, self.cls.__dict__.values()):
            self.subcommands.append(subcommand)
        if self.arguments and self.subcommands:
            raise RuntimeError("Commands with arguments and subclasses are not supported")

    @property
    def module(self):
        return self._module

    @module.setter
    def module(self, value):
        self._module = value
        for subcommand in self.subcommands:
            subcommand.module = value

    def is_allowed(self, message: discord.Message):
        return self.cls.is_allowed(message)

    def execute(self, ctx: CommandContext): # TODO
        return self.cls.execute(ctx)