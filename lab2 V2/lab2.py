from enum import Enum
from typing import Tuple


# === 1. Enum для цветов текста ===
class Color(Enum):
    RED = '\u001b[31m'
    GREEN = '\u001b[32m'
    YELLOW = '\u001b[33m'
    BLUE = '\u001b[34m'
    MAGENTA = '\u001b[35m'
    CYAN = '\u001b[36m'
    RESET = '\u001b[0m'


# === 2. Enum для размеров шрифта ===
class FontSize(Enum):
    SMALL = 'small.txt'
    BIG = 'big.txt'


# === 3. Загрузка псевдошрифта из файла ===
def load_font_template(file_path: str) -> dict:
    font = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_char = None
    buffer = []

    for line in lines:
        if line.startswith('#'):
            continue
        if line.strip().startswith('CHAR:'):
            if current_char:
                font[current_char] = buffer
            current_char = line.strip().split(':')[1].strip()
            buffer = []
        elif line.strip():
            buffer.append(line.rstrip('\n'))

    if current_char:
        font[current_char] = buffer

    return font


# === 4. Класс Printer ===
class Printer:
    _font_cache = {}

    @staticmethod
    def _get_font(font_size: FontSize) -> dict:
        if font_size not in Printer._font_cache:
            Printer._font_cache[font_size] = load_font_template(font_size.value)
        return Printer._font_cache[font_size]

    def __init__(self, color: Color, position: Tuple[int, int], symbol: str = '*', font_size: FontSize = FontSize.BIG):
        self.color = color
        self.position = position
        self.symbol = symbol
        self.font_size = font_size
        self.font = Printer._get_font(font_size)

    def __enter__(self):
        self._save_cursor_position()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._restore_cursor_position()
        print(Color.RESET.value, end='')

    @staticmethod
    def print(text: str, color: Color, position: Tuple[int, int], symbol: str = '*', font_size: FontSize = FontSize.BIG):
        font = Printer._get_font(font_size)
        Printer._move_cursor(position)
        Printer._print_big_text(text, color, symbol, font)

    def print_text(self, text: str):
        Printer._move_cursor(self.position)
        Printer._print_big_text(text, self.color, self.symbol, self.font)

    @staticmethod
    def _print_big_text(text: str, color: Color, symbol: str, font: dict):
        height = max(len(font.get(char.upper(), [])) for char in text)

        for row in range(height):
            for char in text:
                pattern = font.get(char.upper(), ['?'] * height)
                if row < len(pattern):
                    line = pattern[row].replace('*', symbol)
                    print(f"{color.value}{line}{Color.RESET.value} ", end='')
                else:
                    print(' ' * len(pattern[0]), end=' ')
            print()

    @staticmethod
    def _move_cursor(position: Tuple[int, int]):
        row, col = position
        print(f"\u001b[{row};{col}H", end='')

    def _save_cursor_position(self):
        print("\u001b[s", end='')

    def _restore_cursor_position(self):
        print("\u001b[u", end='')


# === 5. Демонстрация ===
def main():
    print("\u001b[2J")  # Очистка экрана

    # Маленький шрифт
    Printer.print("Hi", Color.CYAN, (2, 5), symbol='@', font_size=FontSize.SMALL)

    # Большой шрифт
    Printer.print("BIG", Color.GREEN, (8, 5), symbol='#', font_size=FontSize.BIG)

    # С контекстом
    with Printer(Color.MAGENTA, (15, 10), symbol='&', font_size=FontSize.BIG) as printer:
        printer.print_text("Bye")

    # С контекстом и маленьким шрифтом
    with Printer(Color.YELLOW, (22, 5), symbol='*', font_size=FontSize.SMALL) as printer:
        printer.print_text("ok")


if __name__ == '__main__':
    main()
