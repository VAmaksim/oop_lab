from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
import json
from pathlib import Path


# --- Состояние клавиатуры ---
class KeyboardState:
    def __init__(self):
        self.output = ""
        self.cursor = 0
        self.volume = 50
        self.media_running = False


# --- Интерфейс команды ---
class Command(ABC):
    @abstractmethod
    def execute(self, state: KeyboardState) -> str:
        pass

    @abstractmethod
    def undo(self, state: KeyboardState) -> str:
        pass


# --- Команда печати символа ---
class PrintCharCommand(Command):
    def __init__(self, char: str):
        self.char = char
        self.position = None

    def execute(self, state: KeyboardState) -> str:
        if self.position is None:
            self.position = state.cursor
        state.output = (
            state.output[:self.position] + self.char + state.output[self.position:]
        )
        state.cursor = self.position + 1
        return state.output

    def undo(self, state: KeyboardState) -> str:
        if self.position is not None and self.position < len(state.output):
            state.output = (
                state.output[:self.position] + state.output[self.position + 1:]
            )
            state.cursor = max(0, self.position)
        return state.output


# --- Команда увеличения громкости ---
class VolumeUpCommand(Command):
    def execute(self, state: KeyboardState) -> str:
        state.volume = min(100, state.volume + 20)
        return f"volume increased +20% (current: {state.volume}%)"

    def undo(self, state: KeyboardState) -> str:
        state.volume = max(0, state.volume - 20)
        return f"volume decreased -20% (current: {state.volume}%)"


# --- Команда уменьшения громкости ---
class VolumeDownCommand(Command):
    def execute(self, state: KeyboardState) -> str:
        state.volume = max(0, state.volume - 20)
        return f"volume decreased -20% (current: {state.volume}%)"

    def undo(self, state: KeyboardState) -> str:
        state.volume = min(100, state.volume + 20)
        return f"volume increased +20% (current: {state.volume}%)"


# --- Команда медиа-плеера ---
class MediaPlayerCommand(Command):
    def __init__(self):
        self.was_running = False

    def execute(self, state: KeyboardState) -> str:
        self.was_running = state.media_running
        if not state.media_running:
            state.media_running = True
            return "media player launched"
        return "media player already running"

    def undo(self, state: KeyboardState) -> str:
        if not self.was_running and state.media_running:
            state.media_running = False
            return "media player closed"
        return "media player was not running"


# --- Memento: сохраняем только ассоциации ---
class KeyboardStateSaver:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

    def save(self, associations: Dict[str, Dict[str, Any]]):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(associations, f, ensure_ascii=False, indent=2)

    def load(self) -> Dict[str, Dict[str, Any]]:
        if self.filepath.exists():
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


# --- Фабрика команд ---
class CommandFactory:
    def __init__(self):
        self.registry: Dict[str, Callable[[Any], Command]] = {}

    def register(self, name: str, constructor: Callable[[Any], Command]):
        self.registry[name] = constructor

    def create(self, desc: Dict[str, Any]) -> Command:
        cmd_name = desc["command"]
        arg = desc.get("arg")
        if cmd_name in self.registry:
            return self.registry[cmd_name](arg)
        raise ValueError(f"Unknown command: {cmd_name}")


# --- Класс клавиатуры ---
class Keyboard:
    def __init__(
        self,
        assoc_file: str,
        command_factory: CommandFactory,
        log_file: Optional[str] = None,
    ):
        self.state = KeyboardState()
        self.state_saver = KeyboardStateSaver(assoc_file)
        self.associations: Dict[str, Dict[str, Any]] = self.state_saver.load()

        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []

        self.factory = command_factory

        self.log_f = open(log_file, 'a', encoding='utf-8') if log_file else None

    def log(self, text: str):
        print(text)
        if self.log_f:
            self.log_f.write(text + "\n")
            self.log_f.flush()

    def set_association_desc(self, key: str, desc: Dict[str, Any]):
        self.associations[key] = desc
        self.state_saver.save(self.associations)
        self.log(f"set: {key} -> {desc}")

    def press_key(self, key: str):
        desc = self.associations.get(key)
        if not desc:
            self.log(f"unknown key: {key}")
            return

        try:
            command = self.factory.create(desc)
        except ValueError as e:
            self.log(f"error: {e}")
            return

        result = command.execute(self.state)

        self.undo_stack.append(command)
        self.redo_stack.clear()

        self.log(key)
        self.log(result)

    def undo(self):
        if not self.undo_stack:
            self.log("undo")
            self.log("nothing to undo")
            return
        command = self.undo_stack.pop()
        result = command.undo(self.state)
        self.redo_stack.append(command)
        self.log("undo")
        self.log(result)

    def redo(self):
        if not self.redo_stack:
            self.log("redo")
            self.log("nothing to redo")
            return
        command = self.redo_stack.pop()
        result = command.execute(self.state)
        self.undo_stack.append(command)
        self.log("redo")
        self.log(result)

    def close(self):
        if self.log_f:
            self.log_f.close()


# --- Пример использования ---
if __name__ == "__main__":
    factory = CommandFactory()
    factory.register("char", lambda arg: PrintCharCommand(arg))
    factory.register("volume_up", lambda arg: VolumeUpCommand())
    factory.register("volume_down", lambda arg: VolumeDownCommand())
    factory.register("media_player", lambda arg: MediaPlayerCommand())

    kb = Keyboard("associations.json", factory, "log.txt")

    kb.set_association_desc("a", {"command": "char", "arg": "a"})
    kb.set_association_desc("b", {"command": "char", "arg": "b"})
    kb.set_association_desc("c", {"command": "char", "arg": "c"})
    kb.set_association_desc("d", {"command": "char", "arg": "d"})
    kb.set_association_desc("ctrl++", {"command": "volume_up"})
    kb.set_association_desc("ctrl+-", {"command": "volume_down"})
    kb.set_association_desc("ctrl+p", {"command": "media_player"})

    kb.press_key("a")
    kb.press_key("b")
    kb.press_key("c")
    kb.undo()
    kb.undo()
    kb.redo()
    kb.press_key("ctrl++")
    kb.press_key("ctrl+-")
    kb.press_key("ctrl+p")
    kb.press_key("d")
    kb.undo()
    kb.undo()

    kb.close()
