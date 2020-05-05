import textgenrnn

from decorators import mrvn_module
from modular import Module, Command, CommandContext, CommandResult


@mrvn_module("Textgenrnn AI", "ИИ.")
class TextgenrnnAI(Module):
    async def on_enable(self):
        class AICommand(Command):
            title: str
            file_name: str
            color: int
            model: textgenrnn.textgenrnn

            model_loaded = True

            def __init__(self, title, file_name, command_name, color, module):
                super().__init__(command_name, "ИИ %s" % title, args_description="[prefix=<префикс>]", module=module)

                self.title = title
                self.file_name = file_name
                self.color = color

                try:
                    self.model = textgenrnn.textgenrnn(weights_path="%s_weights.hdf5" % file_name,
                                                       vocab_path="%s_vocab.json" % file_name,
                                                       config_path="%s_config.json" % file_name)
                except FileNotFoundError:
                    self.module.logger.error("Не удалось найти модель ИИ %s. Команда не будет работать." % title)

                    self.model_loaded = False
                else:
                    self.module.logger.ok("Загружена модель ИИ %s." % title)

                self.module.bot.command_handler.register_command(self)

            async def execute(self, ctx: CommandContext) -> CommandResult:
                if not self.model_loaded:
                    return CommandResult.error("Этот ИИ не загружен.")

                prefix = None

                if len(ctx.clean_args) > 0 and ctx.clean_args[0].startswith("prefix="):
                    prefix = " ".join(ctx.clean_args)[7:]

                output = self.model.generate(temperature=self.module.bot.module_handler.get_param("ai_temp"),
                                             return_as_list=True,
                                             prefix=prefix)[0]

                embed = ctx.get_custom_embed(output, "ИИ %s" % self.title, self.color)

                await ctx.message.channel.send(embed=embed)
                return CommandResult.ok()

        self.bot.module_handler.add_param("ai_temp", 0.9)

        models = [AICommand("Kaizen", "kaizen", "kz", 0x64E3E1, self),
                  AICommand("Icarus", "icarus", "ic", 0xFFD700, self)]
