from dataclasses import dataclass, field, asdict
from typing import Protocol, Optional, TypeVar, Generic, Sequence
from pathlib import Path
import json

# --- Шаг 1: Класс User ---
@dataclass(order=True)
class User:
    name: str
    id: int = field(compare=False)
    login: str = field(compare=False)
    password: str = field(repr=False, compare=False)
    email: Optional[str] = field(default=None, compare=False)
    address: Optional[str] = field(default=None, compare=False)

    def to_dict(self):
        data = asdict(self)
        # Не удаляем password, т.к. нужно для авторизации, но не выводим его в repr
        return data

    def __repr__(self):
        return (f"User(id={self.id}, name={self.name!r}, login={self.login!r}, "
                f"email={self.email!r}, address={self.address!r})")

# --- Шаг 2: Протокол CRUD ---
T = TypeVar('T')

class DataRepositoryProtocol(Protocol, Generic[T]):
    def get_all(self) -> Sequence[T]: ...
    def get_by_id(self, id: int) -> Optional[T]: ...
    def add(self, item: T) -> None: ...
    def update(self, item: T) -> None: ...
    def delete(self, item: T) -> None: ...

# --- Шаг 3: Протокол UserRepository ---
class UserRepositoryProtocol(DataRepositoryProtocol[User], Protocol):
    def get_by_login(self, login: str) -> Optional[User]: ...

# --- Шаг 4: Реализация DataRepository ---
class DataRepository(Generic[T]):
    def __init__(self, path: str, cls: type[T]):
        self.path = Path(path)
        self._cls = cls
        self._data: list[T] = []
        self.load()

    def load(self):
        try:
            if self.path.exists() and self.path.read_text(encoding='utf-8').strip():
                with open(self.path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    if not isinstance(raw, list):
                        raise ValueError("Данные должны быть списком")
                    self._data = [self._cls(**item) for item in raw]
        except (json.JSONDecodeError, OSError, ValueError) as e:
            print(f"Ошибка при загрузке данных из {self.path}: {e}")

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump([obj.to_dict() for obj in self._data], f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Ошибка при сохранении данных в {self.path}: {e}")

    def get_all(self) -> Sequence[T]:
        return list(self._data)

    def get_by_id(self, id: int) -> Optional[T]:
        return next((item for item in self._data if item.id == id), None)

    def add(self, item: T) -> None:
        if self.get_by_id(item.id) is not None:
            raise ValueError(f"Объект с id={item.id} уже существует")
        self._data.append(item)
        self.save()

    def update(self, item: T) -> None:
        for i, old in enumerate(self._data):
            if old.id == item.id:
                self._data[i] = item
                self.save()
                return
        raise ValueError(f"Объект с id={item.id} не найден")

    def delete(self, item: T) -> None:
        initial_len = len(self._data)
        self._data = [x for x in self._data if x.id != item.id]
        if len(self._data) < initial_len:
            self.save()

# --- Шаг 5: Реализация UserRepository ---
class UserRepository(UserRepositoryProtocol):
    def __init__(self, path: str):
        self._repo = DataRepository[User](path, User)

    def get_all(self) -> Sequence[User]:
        return self._repo.get_all()

    def get_by_id(self, id: int) -> Optional[User]:
        return self._repo.get_by_id(id)

    def add(self, item: User) -> None:
        if self._repo.get_by_id(item.id) is not None:
            raise ValueError(f"Пользователь с id={item.id} уже существует")
        if self.get_by_login(item.login) is not None:
            raise ValueError(f"Пользователь с login={item.login} уже существует")
        self._repo.add(item)

    def update(self, item: User) -> None:
        # Проверка, что логин уникален (если меняется login)
        existing_user = self.get_by_login(item.login)
        if existing_user and existing_user.id != item.id:
            raise ValueError(f"Пользователь с login={item.login} уже существует")
        self._repo.update(item)

    def delete(self, item: User) -> None:
        self._repo.delete(item)

    def get_by_login(self, login: str) -> Optional[User]:
        return next((u for u in self._repo.get_all() if u.login == login), None)

# --- Шаг 6: Протокол AuthService ---
class AuthServiceProtocol(Protocol):
    def sign_in(self, login: str, password: str) -> None: ...
    def sign_out(self) -> None: ...
    @property
    def is_authorized(self) -> bool: ...
    @property
    def current_user(self) -> Optional[User]: ...

# --- Шаг 7: Реализация AuthService ---
class AuthService(AuthServiceProtocol):
    def __init__(self, session_file: str, user_repo: UserRepositoryProtocol):
        self._session_path = Path(session_file)
        self._current_user: Optional[User] = None
        self._user_repo = user_repo
        self._load_session()

    def _load_session(self):
        try:
            if self._session_path.exists():
                with open(self._session_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    user_id = raw.get("user_id")
                    if user_id is not None:
                        user = self._user_repo.get_by_id(user_id)
                        if user:
                            self._current_user = user
        except (json.JSONDecodeError, OSError) as e:
            print(f"Ошибка при загрузке сессии: {e}")

    def _save_session(self):
        try:
            if self._current_user:
                with open(self._session_path, 'w', encoding='utf-8') as f:
                    json.dump({"user_id": self._current_user.id}, f, ensure_ascii=False, indent=2)
            else:
                if self._session_path.exists():
                    self._session_path.unlink()
        except OSError as e:
            print(f"Ошибка при сохранении сессии: {e}")

    def sign_in(self, login: str, password: str) -> None:
        user = self._user_repo.get_by_login(login)
        if user is None:
            raise ValueError("Пользователь не найден")
        if user.password != password:
            raise ValueError("Неверный пароль")
        self._current_user = user
        self._save_session()

    def sign_out(self) -> None:
        self._current_user = None
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except OSError as e:
            print(f"Ошибка при удалении сессии: {e}")

    @property
    def is_authorized(self) -> bool:
        return self._current_user is not None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

# --- Шаг 8: Демонстрация ---
if __name__ == "__main__":
    import os

    # Очистка файлов перед демонстрацией
    for f in ("users.json", "session.json"):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    repo = UserRepository("users.json")
    auth = AuthService("session.json", repo)

    # Добавление пользователя
    user1 = User(id=1, name="Alice", login="alice", password="1234", email="a@mail.com")
    try:
        repo.add(user1)
        print("Пользователь добавлен:", user1)
    except ValueError as e:
        print(e)

    # Обновление пользователя
    user1.name = "Alice Smith"
    try:
        repo.update(user1)
        print("Пользователь обновлен:", user1)
    except ValueError as e:
        print(e)

    # Авторизация пользователя (по login и password)
    try:
        auth.sign_in("alice", "1234")
        print("Авторизован:", auth.is_authorized)
        print("Текущий пользователь:", auth.current_user)
    except ValueError as e:
        print("Ошибка авторизации:", e)

    # Добавление второго пользователя и смена
    user2 = User(id=2, name="Bob", login="bob", password="0000")
    try:
        repo.add(user2)
        print("Пользователь добавлен:", user2)
    except ValueError as e:
        print(e)

    try:
        auth.sign_in("bob", "0000")
        print("Сменили пользователя:", auth.current_user)
    except ValueError as e:
        print("Ошибка авторизации:", e)

    # Проверка автоматической авторизации при перезапуске AuthService
    auth2 = AuthService("session.json", repo)
    print("Автоавторизация:", auth2.is_authorized)
    print("Пользователь после перезапуска:", auth2.current_user)

    # Сортировка пользователей по имени
    print("Отсортированные пользователи:", sorted(repo.get_all()))

    # Удаление пользователя
    repo.delete(user2)
    print("Пользователи после удаления:", repo.get_all())
