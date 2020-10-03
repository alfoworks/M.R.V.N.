class MrvnConfig:
    modules_dirs = ["mrvn_modules"]  # Папка, откуда будут загружаться модули.
    ignored_modules = [""]  # ИМЕНА ФАЙЛОВ модулей, которые будут проигнорированы при загрузке.
    github_login = ""
    github_password = ""
    guild_whitelist = []  # Белый список серверов

    @staticmethod
    def get_token() -> str:  # Функция получения токена. Сюда можно вставить любой код, но можно просто вернуть строку.
        return ""
