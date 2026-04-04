"""Qt i18n: load .qm when present, otherwise embedded Russian strings (TASK-010 / PRD 3.11.9)."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QLocale, QTranslator


def translations_dir() -> Path:
    return Path(__file__).resolve().parent / "translations"


def want_russian() -> bool:
    loc = QLocale.system()
    if loc.language() == QLocale.Russian:
        return True
    for key in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        v = os.environ.get(key, "")
        if v and v.lower().split(".")[0].split("_")[0] == "ru":
            return True
    return False


# (context, source) -> Russian. Empty value from translate() means "use source English".
_RU: dict[tuple[str, str], str] = {
    ("main", "Ok"): "Ок",
    (
        "main",
        "xgamma is not installed or not found in PATH.\n\n"
        "Please install xgamma using one of the following commands:\n\n"
        "Ubuntu/Debian: sudo apt-get install x11-xserver-utils\n"
        "Fedora: sudo dnf install xorg-x11-server-utils\n"
        "Arch Linux: sudo pacman -S xorg-xgamma\n\n"
        "After installation, please restart the application.",
    ): (
        "xgamma не установлен или не найден в PATH.\n\n"
        "Установите xgamma одной из команд:\n\n"
        "Ubuntu/Debian: sudo apt-get install x11-xserver-utils\n"
        "Fedora: sudo dnf install xorg-x11-server-utils\n"
        "Arch Linux: sudo pacman -S xorg-xgamma\n\n"
        "После установки перезапустите приложение."
    ),
    ("main", "xgamma GUI Tool - Missing Dependency"): "xgamma GUI Tool — нет зависимости",
    ("main", "xgamma Not Found"): "xgamma не найден",
    ("GammaMainWindow", "xgamma GUI Tool"): "xgamma GUI Tool",
    ("GammaMainWindow", "Settings"): "Настройки",
    ("GammaMainWindow", "Dismiss"): "Скрыть",
    (
        "GammaMainWindow",
        "Hide this notice. The warning icon stays for details.",
    ): "Скрыть это сообщение. Значок предупреждения останется для подробностей.",
    ("GammaMainWindow", "Reading display gamma…"): "Чтение гаммы дисплея…",
    ("GammaMainWindow", "Red"): "Красный",
    ("GammaMainWindow", "Green"): "Зелёный",
    ("GammaMainWindow", "Blue"): "Синий",
    ("GammaMainWindow", "All"): "Все",
    (
        "GammaMainWindow",
        "Focus this row (Tab or click the label), then use ←/→ to adjust gamma; "
        "hold Shift for larger steps.",
    ): (
        "Выберите строку (Tab или клик по подписи), затем ←/→ для изменения гаммы; "
        "удерживайте Shift для большего шага."
    ),
    (
        "GammaMainWindow",
        "While Red, Green, and Blue differ, this row shows their arithmetic average. "
        "Moving the All slider sets all three channels to the same gamma value.",
    ): (
        "Пока красный, зелёный и синий различаются, здесь показано среднее арифметическое. "
        "Перемещение ползунка «Все» выставляет одинаковую гамму для всех трёх каналов."
    ),
    (
        "GammaMainWindow",
        "Average when R/G/B differ; dragging All sets all three channels equal.",
    ): (
        "Среднее при различии R/G/B; перетаскивание «Все» выравнивает все три канала."
    ),
    ("GammaMainWindow", "Reset"): "Сброс",
    ("GammaMainWindow", "Apply"): "Применить",
    ("GammaMainWindow", "Loading initial settings…"): "Загрузка начальных параметров…",
    ("GammaMainWindow", " Environment may limit gamma — see the notice above."): (
        " Окружение может ограничивать гамму — см. уведомление выше."
    ),
    ("GammaMainWindow", "Ready"): "Готово",
    (
        "GammaMainWindow",
        "Gamma from xrandr (xgamma output was not recognized).",
    ): "Гамма из xrandr (вывод xgamma не распознан).",
    (
        "GammaMainWindow",
        "Could not read display gamma; defaults (1.0) shown. "
        "Check DISPLAY and xgamma.",
    ): (
        "Не удалось прочитать гамму дисплея; показаны значения по умолчанию (1.0). "
        "Проверьте DISPLAY и xgamma."
    ),
    ("GammaMainWindow", "Could not apply gamma to the display."): (
        "Не удалось применить гамму к дисплею."
    ),
    ("GammaMainWindow", "Display environment"): "Окружение дисплея",
    ("GammaMainWindow", "Could not remove autostart ({})."): (
        "Не удалось удалить автозапуск ({})."
    ),
    ("GammaMainWindow", " — Autostart: {}."): " — Автозапуск: {}.",
    ("GammaMainWindow", "Reset to defaults and removed from autostart"): (
        "Сброшено к значениям по умолчанию, автозапуск удалён"
    ),
    ("GammaMainWindow", "Reset to defaults"): "Сброшено к значениям по умолчанию",
    ("GammaMainWindow", "Error: xgamma not available"): "Ошибка: xgamma недоступен",
    (
        "GammaMainWindow",
        "Settings applied and saved to autostart",
    ): "Параметры применены и сохранены в автозапуск",
    (
        "GammaMainWindow",
        "Could not save to autostart ({}). See log for details.",
    ): "Не удалось сохранить в автозапуск ({}). Подробности в журнале.",
    (
        "environment",
        "VM environment may limit gamma adjustment.",
    ): "Виртуальная машина может ограничивать настройку гаммы.",
    (
        "environment",
        "HDR or 10-bit mode may disable manual gamma adjustment.",
    ): "Режим HDR или 10 бит может отключить ручную настройку гаммы.",
    ("AboutDialog", "About xgamma GUI Tool"): "О программе — xgamma GUI Tool",
    ("AboutDialog", "xgamma GUI Tool"): "xgamma GUI Tool",
    ("AboutDialog", "Version:"): "Версия:",
    ("AboutDialog", "Project on GitHub"): "Проект на GitHub",
    ("AboutDialog", "Author: pgorithm"): "Автор: pgorithm",
    ("SettingsDialog", "Settings"): "Настройки",
    ("SettingsDialog", "About"): "О программе",
    (
        "SettingsDialog",
        "Open version and project information",
    ): "Открыть версию и сведения о проекте",
}


class EmbeddedRussianTranslator(QTranslator):
    """In-process Russian catalog when no .qm is shipped or load fails."""

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if n >= 0:
            return ""
        key = (context, sourceText)
        return _RU.get(key, "")


def install_translators(app) -> None:
    """Install Qt translators before creating UI. Honors Russian locale / LANG=ru."""
    if not want_russian():
        return

    qm_path = translations_dir() / "xgamma_gui_ru.qm"
    loaded = False
    if qm_path.is_file():
        tr_file = QTranslator()
        if tr_file.load(str(qm_path)):
            app.installTranslator(tr_file)
            loaded = True

    if not loaded:
        app.installTranslator(EmbeddedRussianTranslator())
