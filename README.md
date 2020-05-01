# M.R.V.N.
Модульный Discord бот.
## Документация
### Пример модуля с командой
```python
from decorators import mrvn_module, mrvn_command
from modular import Module, LanguageUtils, Command, CommandResult, CommandContext


@mrvn_module("TestModule", "Тестовый модуль")
class TestModule(Module):
    async def on_enable(self):
        self.logger.info("Модуль запущен!")

        @mrvn_command(self, "test", "Тестовая команда")
        class TestCommand(Command):
            async def execute(self, ctx: CommandContext) -> CommandResult:
                return CommandResult.info("Беу!")

```
### Декораторы
`@mrvn_module(name: str, desc: str)` - декоратор, обозначающий модуль. Необходимо использовать с классом, наследующим `modular.Module`

Описание параметров:
* `name` - имя модуля
* `desc` - описание модуля

`@mrvn_command(module: modular.Module, name: str, desc: str, args_desc: str = "", keys_desc=None,
                 perm_handler: modular.PermissionHandler = None, should_await: bool = True)`
                 
 Описание параметров:
 * `module` - модуль команды
 * `name` - имя команды (без пробелов, в нижнем регистре)
 * `desc` - описание команды
 * `args_desc` - **описание** аргументов команды
 * `keys_desc` - список ключей команды для описания
 * `perm_handler` - PermissionHandler команды. Используется для проверки прав пользователя.
 * `should_await` - сообщает CommandHandler'у, стоит ли ожидать завершения команды. Если указано False, то ждать никто не будет, а в качестве результата будет использовано `CommandResult.ok()`

To Be Continued (ну как обычно)