from typing import Protocol, List
import re
import sys
import socket
from datetime import datetime


class LogFilterProtocol(Protocol):
    def match(self, text: str) -> bool:
        pass


class SimpleLogFilter(LogFilterProtocol):
    def __init__(self, pattern: str):
        self.pattern = pattern

    def match(self, text: str) -> bool:
        return self.pattern in text


class ReLogFilter(LogFilterProtocol):
    def __init__(self, pattern: str):
        self.regex = re.compile(pattern)

    def match(self, text: str) -> bool:
        return bool(self.regex.search(text))


class LevelFilter(LogFilterProtocol):
    def __init__(self, level: str):
        self.level = level.upper()

    def match(self, text: str) -> bool:
        return text.startswith(self.level)


class LogHandlerProtocol(Protocol):
    def handle(self, text: str):
        pass


class FileHandler(LogHandlerProtocol):
    def __init__(self, filename: str):
        self.filename = filename

    def _handle(self, text: str):
        with open(self.filename, "a", encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")

    def handle(self, text: str):
        try:
            self._handle(text)
        except (IOError, PermissionError) as e:
            sys.stderr.write(f"FileHandler error: {e}\n")


class SocketHandler(LogHandlerProtocol):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def handle(self, text: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)  # Таймаут 1 секунда
                s.connect((self.host, self.port))
                s.sendall(f"{text}\n".encode('utf-8'))
        except (socket.error, ConnectionRefusedError, TimeoutError) as e:
            sys.stderr.write(f"SocketHandler error: {e}\n")


class ConsoleHandler(LogHandlerProtocol):
    def __init__(self, use_stderr: bool = False):
        self.use_stderr = use_stderr

    def handle(self, text: str):
        if self.use_stderr:
            sys.stderr.write(f"{text}\n")
        else:
            print(text)


class SyslogHandler(LogHandlerProtocol):
    def handle(self, text: str):
        sys.stderr.write(f"SYSLOG: {text}\n")


class Logger:
    def __init__(self, _filters: List[LogFilterProtocol], _handlers: List[LogHandlerProtocol]):
        self.__filters = _filters
        self.__handlers = _handlers

    def log(self, text: str):
        if all(f.match(text) for f in self.__filters):
            for handler in self.__handlers:
                handler.handle(text)


if __name__ == "__main__":
    print("Демонстрация работы системы логирования")

    # Создаем различные фильтры
    error_filter = SimpleLogFilter("ERROR")
    warning_filter = SimpleLogFilter("WARNING")
    digit_filter = ReLogFilter(r"\d+")
    level_filter = LevelFilter("INFO")

    # Обработчики
    console_handler = ConsoleHandler()
    error_file_handler = FileHandler("error_logs.txt")
    all_file_handler = FileHandler("all_logs.txt")
    syslog_handler = SyslogHandler()

    # Логировать только ERROR сообщения с цифрами в консоль и файл
    print("\nПример 1: ERROR логи с цифрами")
    logger1 = Logger(
        [error_filter, digit_filter],
        [console_handler, error_file_handler]
    )

    logger1.log("ERROR: Сервер вернул код 500")
    logger1.log("WARNING: Незначительная проблема в системе")
    logger1.log("ERROR: Ошибка соединения 503")

    # Логировать все INFO сообщения в файл и syslog
    print("\nПример 2: INFO логи")
    logger2 = Logger(
        [level_filter],
        [all_file_handler, syslog_handler]
    )

    logger2.log("INFO: Запуск модуля аутентификации")
    logger2.log("INFO: Загрузка конфигурации завершена")
    logger2.log("WARNING: Высокая загрузка CPU")

    # Логировать все сообщения в консоль
    print("\nПример 3: Все логи")
    logger3 = Logger(
        [],
        [console_handler]
    )

    logger3.log("DEBUG: Инициализация кеша")
    logger3.log("INFO: Новый пользователь зарегистрирован")
    logger3.log("ERROR: Не удалось подключиться к базе данных")
