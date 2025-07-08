from typing import Optional, Protocol, TypeVar, Sequence, Self
from dataclasses import dataclass, field
from functools import total_ordering
import os, json

T = TypeVar('T')
ID = "id"
LOGIN = "login"

@dataclass
@total_ordering
class User:
    id: int
    login: str
    password: str = field(repr=False, compare=False)
    name: str = field(compare=False)
    email: Optional[str] = field(default=None, compare=False)
    address: Optional[str] = field(default=None, compare=False)

    def __lt__(self, other: Self) -> bool:
        return self.name.lower() < other.name.lower()

class DataRepositoryProtocol(Protocol[T]):
    def get_all(self) -> Sequence[T]: ...
    def get_by_id(self, id: int) -> Optional[T]: ...
    def add(self, item: T) -> None: ...
    def update(self, item: T) -> None: ...
    def delete(self, item: T) -> None: ...

class DataRepository(DataRepositoryProtocol[T]):
    def __init__(self, file_path: str, T: type) -> None:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        self.file_path = file_path
        self.T = T
        self._data = self._load_data()

    def _load_data(self) -> list[dict]:
        try:
            with open(self.file_path, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_data(self) -> None:
        with open(self.file_path, 'w') as file:
            json.dump(self._data, file, indent=2)

    def get_all(self) -> Sequence[T]:
        return [self.T(**item) for item in self._load_data()]

    def get_by_id(self, id: int) -> Optional[T]:
        for item in self._load_data():
            if item[ID] == id:
                return self.T(**item)
        return None

    def add(self, item: T) -> None:
        self._data.append(item.__dict__)
        self._save_data()

    def update(self, item: T) -> None:
        for i, entry in enumerate(self._data):
            if entry[ID] == item.id:
                self._data[i] = item.__dict__
                break
        self._save_data()

    def delete(self, item: T) -> None:
        self._data = [elem for elem in self._data if elem[ID] != item.id]
        self._save_data()

class UserRepositoryProtocol(DataRepositoryProtocol[User], Protocol):
    def get_by_login(self, login: str) -> Optional[User]: ...

class UserRepository(DataRepository[User], UserRepositoryProtocol):
    def __init__(self, file_path: str = 'data/users.json') -> None:
        super().__init__(file_path, User)

    def get_by_login(self, login: str) -> Optional[User]:
        for item in self._load_data():
            if item[LOGIN] == login:
                return User(**item)
        return None

class AuthServiceProtocol(Protocol):
    def sign_in(self, login: str, password: str) -> bool: ...
    def sign_out(self) -> None: ...
    @property
    def is_authorized(self) -> bool: ...
    @property
    def current_user(self) -> Optional[User]: ...

class AuthService(AuthServiceProtocol):
    def __init__(self, user_repo: UserRepositoryProtocol, session_file: str = 'data/session.json') -> None:
        dir_name = os.path.dirname(session_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        self.SESSION_FILE = session_file
        self.user_repo = user_repo
        self._current_user: Optional[User] = None
        self._load_session()

    def _load_session(self) -> None:
        try:
            with open(self.SESSION_FILE, 'r') as f:
                session = json.load(f)
                self._current_user = self.user_repo.get_by_id(session['user_id'])
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self._current_user = None

    def _save_session(self) -> None:
        if not self._current_user:
            return
        with open(self.SESSION_FILE, 'w') as file:
            json.dump({'user_id': self._current_user.id}, file)

    def sign_in(self, login: str, password: str) -> bool:
        user = self.user_repo.get_by_login(login)
        if user and user.password == password:
            self._current_user = user
            self._save_session()
            return True
        return False

    def sign_out(self) -> None:
        self._current_user = None
        try:
            os.remove(self.SESSION_FILE)
        except FileNotFoundError:
            pass

    @property
    def is_authorized(self) -> bool:
        return self._current_user is not None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

COLORING = "\033[{}m{}\033[0m"
def text_color(text: str) -> str:
    return COLORING.format(33, text)
def beautiful_bool(value: bool) -> str:
    return COLORING.format(32 if value else 31, "True" if value else "False")
def beautiful_none(value: Optional[str]) -> str:
    return COLORING.format(33 if value is None else 32, str(value))

STYLE = "\033[{}m{}\033[0m"

def fx_label(msg: str) -> str:
    return STYLE.format(35, msg)  # Magenta

def fx_status(ok: bool) -> str:
    return STYLE.format(36 if ok else 31, "OK" if ok else "FAIL")  # Cyan/Red

def fx_object(obj: Optional[str]) -> str:
    return STYLE.format(33 if obj is None else 32, str(obj))  # Yellow/Green

if __name__ == "__main__":
    storage = UserRepository()
    gatekeeper = AuthService(storage)

    initial_pool = [
        User(100, "root", "toor", "Chief System", "sys@internal.local"),
        User(101, "guest123", "letmein", "Valeriy Z.", "contact@somewhere.net", "Hidden Base 7"),
        User(102, "alpha_wolf", "hunterX", "Kirill M.", "alpha@packmail.org", "Sector-8 Warehouse"),
        User(103, "echo99", "mirrorMe", "Nadia T.", "echo@loopback.io", "The Overlook, Room 302"),
        User(104, "xeno_ops", "passXeno", "Operator X", "x.ops@outpost.zone", "Labyrinth Node 13"),
        User(105, "lynx_dev", "c0d3base", "T. Volkov", "lynx@devlabs.dev", "Stacktrace Blvd 21")
    ]

    for entity in initial_pool:
        if not storage.get_by_id(entity.id):
            storage.add(entity)

    print(fx_label(">>> SESSION RECOVERY <<<"))
    print("Authorized:", fx_status(gatekeeper.is_authorized))
    print("User object:", fx_object(gatekeeper.current_user))
    print()

    print(fx_label(">>> LOGIN ATTEMPT: wrong password <<<"))
    print("Login result:", fx_status(gatekeeper.sign_in("root", "wrong123")))
    print("Auth check:", fx_status(gatekeeper.is_authorized))
    print("Active:", fx_object(gatekeeper.current_user))
    print()

    print(fx_label(">>> LOGIN ATTEMPT: correct credentials <<<"))
    print("Login result:", fx_status(gatekeeper.sign_in("root", "toor")))
    print("Auth check:", fx_status(gatekeeper.is_authorized))
    print("Active:", fx_object(gatekeeper.current_user))
    print()

    print(fx_label(">>> TERMINATING SESSION <<<"))
    gatekeeper.sign_out()
    print("Authorized:", fx_status(gatekeeper.is_authorized))
    print("User:", fx_object(gatekeeper.current_user))
    print()

    print(fx_label(">>> ALT USER LOGIN <<<"))
    print("Login result:", fx_status(gatekeeper.sign_in("guest123", "letmein")))
    print("Session valid:", fx_status(gatekeeper.is_authorized))
    print("User info:", fx_object(gatekeeper.current_user))
    print()

    print(fx_label(">>> DATA ALTERATION <<<"))
    ghost = storage.get_by_login("guest123")
    ghost.name = "Zachary V."
    storage.update(ghost)
    print("Post-update snapshot:")
    print(STYLE.format(36, storage.get_by_id(ghost.id)))

    ghost.name = "Almin G."
    storage.update(ghost)


if __name__ == "__main__":
    demo()
