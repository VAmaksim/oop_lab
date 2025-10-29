import socket
import threading
import time
import re
import sys
from typing import Protocol, List

# --- Протоколы и классы фильтров, обработчиков ---

class LogFilterProtocol(Protocol):
    def match(self, text: str) -> bool:
        ...

class SimpleLogFilter:
    def __init__(self, pattern: str):
        self.pattern = pattern
    def match(self, text: str) -> bool:
        try:
            return self.pattern in text
        except Exception as e:
            print(f"SimpleLogFilter error: {e}", file=sys.stderr)
            return False

class ReLogFilter:
    def __init__(self, pattern: str):
        try:
            self.regex = re.compile(pattern)
        except re.error as e:
            print(f"ReLogFilter init error: {e}", file=sys.stderr)
            self.regex = None

    def match(self, text: str) -> bool:
        try:
            if self.regex:
                return bool(self.regex.search(text))
        except Exception as e:
            print(f"ReLogFilter error: {e}", file=sys.stderr)
        return False


class LogHandlerProtocol(Protocol):
    def handle(self, text: str) -> None:
        ...

class FileHandler:
    def __init__(self, filename: str):
        self.filename = filename
    def handle(self, text: str) -> None:
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(text + '\n')
        except Exception as e:
            print(f"FileHandler error: {e}", file=sys.stderr)

class SocketHandler:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    def handle(self, text: str) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(text.encode('utf-8'))
        except Exception as e:
            print(f"SocketHandler error: {e}", file=sys.stderr)

class ConsoleHandler:
    def handle(self, text: str) -> None:
        try:
            print(text)
        except Exception as e:
            print(f"ConsoleHandler error: {e}", file=sys.stderr)

class SyslogHandler:
    def __init__(self, ident: str = 'MyLogger'):
        self.ident = ident
    def handle(self, text: str) -> None:
        try:
            print(f"[SYSLOG] {self.ident}: {text}")
        except Exception as e:
            print(f"SyslogHandler error: {e}", file=sys.stderr)

class Logger:
    def __init__(self,
                 filters: List[LogFilterProtocol],
                 handlers: List[LogHandlerProtocol]):
        self.filters = filters
        self.handlers = handlers

    def log(self, text: str) -> None:
        try:
            # Фильтруем только если текст проходит все фильтры (AND)
            if all(f.match(text) for f in self.filters):
                for handler in self.handlers:
                    try:
                        handler.handle(text)
                    except Exception as e:
                        print(f"Error in handler {handler.__class__.__name__}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Logger error: {e}", file=sys.stderr)

# --- TCP сервер для SocketHandler ---

def tcp_server(host='localhost', port=9999):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            print(f"Connection from {addr}")
            with conn:
                data = conn.recv(1024)
                if data:
                    print(f"Received from socket: {data.decode()}")

server_thread = threading.Thread(target=tcp_server, daemon=True)
server_thread.start()

time.sleep(1)  # Даем серверу время запуститься

# --- Создаем фильтры и обработчики ---

simple_filter = SimpleLogFilter('ERROR')
regex_filter = ReLogFilter(r'\bWARN(ING)?\b')

console = ConsoleHandler()
file_handler = FileHandler('logs.txt')
syslog_handler = SyslogHandler('Lab3Logger')
socket_handler = SocketHandler('localhost', 9999)

logger = Logger(filters=[simple_filter, regex_filter],
                handlers=[console, file_handler, syslog_handler, socket_handler])

# --- Логируем ---

logger.log("INFO: This is just informational message")   # Не пройдет
logger.log("ERROR: Something went wrong!")                # Не пройдет (не проходит второй фильтр)
logger.log("WARNING: This might be risky!")               # Не пройдет (не проходит первый фильтр)
logger.log("WARN: Low disk space")                         # Не пройдет (не проходит первый фильтр)
logger.log("ERROR WARNING: Critical issue!")              # Пройдет (проходят оба фильтра)
