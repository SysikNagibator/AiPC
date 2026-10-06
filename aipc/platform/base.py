"""Абстракции платформенного кода: швы Screen/Input/Apps.

Реализации: aipc.platform.win32 (полная), aipc.platform.posix (частичная).
Новые платформенные функции добавлять сюда интерфейсом + две реализации,
а не разбрасывать `if os.name` по модулям.
"""
from __future__ import annotations

import abc


class ScreenBackend(abc.ABC):
    """Скриншоты и геометрия мониторов."""

    @abc.abstractmethod
    def shot_monitor(self, monitor: int = 0):
        """PIL.Image всего монитора."""

    @abc.abstractmethod
    def monitors(self) -> list:
        """Список {left, top, width, height}."""


class InputBackend(abc.ABC):
    """Мышь и клавиатура."""

    @abc.abstractmethod
    def move_click(self, x: int, y: int, button: str = "left") -> None:
        """Клик в пикселях."""

    @abc.abstractmethod
    def type_text(self, text: str) -> None:
        """Печать текста."""


class AppBackend(abc.ABC):
    """Запуск приложений и оконные операции."""

    @abc.abstractmethod
    def open(self, target: str) -> None:
        """Открыть приложение/файл/URL средством ОС."""

    @abc.abstractmethod
    def active_title(self) -> str:
        """Заголовок активного окна ('' если недоступно)."""
