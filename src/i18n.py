"""Qt i18n: load .qm when present, otherwise embedded Russian strings (TASK-010 / PRD 3.11.9)."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QCoreApplication, QLocale, QSettings, QTranslator

# Stored in QSettings under SETTINGS_KEY_UI_LANGUAGE (default: follow system / LANG — PRD 3.11.9).
UI_LANGUAGE_SYSTEM = "system"
UI_LANGUAGE_EN = "en"
UI_LANGUAGE_RU = "ru"
QM_LANGUAGE_PREFIX = "qm:"

SETTINGS_KEY_UI_LANGUAGE = "ui_language"
_INSTALLED_TRANSLATORS_ATTR = "_xgamma_installed_translators"


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
        "1.0 means no change for this channel. "
        "Use Red, Green, and Blue to correct tint and white balance; use All to apply "
        "the same factor to every channel. "
        "Focus this row (Tab or click the label), then use ←/→ to adjust gamma; "
        "hold Shift for larger steps.",
    ): (
        "1.0 означает отсутствие изменений для этого канала. "
        "Используйте красный, зелёный и синий для исправления оттенка и баланса белого; "
        "«Все» — чтобы применить один коэффициент ко всем каналам. "
        "Выберите строку (Tab или клик по подписи), затем ←/→ для изменения гаммы; "
        "удерживайте Shift для большего шага."
    ),
    (
        "GammaMainWindow",
        "1.0 neutral; R/G/B for cast, All to scale all channels.",
    ): (
        "1.0 — нейтрально; R/G/B для оттенка, «Все» для масштаба всех каналов."
    ),
    (
        "GammaMainWindow",
        "When Red, Green, and Blue match, 1.0 is neutral for all. "
        "While they differ, this row shows their arithmetic average. "
        "Moving the All slider sets all three channels to the same gamma value. "
        "Focus this row (Tab or click the label), then use ←/→; hold Shift for larger steps.",
    ): (
        "Когда красный, зелёный и синий совпадают, 1.0 нейтрально для всех. "
        "Пока они различаются, здесь показано среднее арифметическое. "
        "Перемещение ползунка «Все» выставляет одинаковую гамму для всех трёх каналов. "
        "Выберите строку (Tab или клик по подписи), затем ←/→; удерживайте Shift для большего шага."
    ),
    (
        "GammaMainWindow",
        "1.0 when matched; average when R/G/B differ; All drag equalizes channels.",
    ): (
        "1.0 при совпадении; среднее при различии R/G/B; перетаскивание «Все» выравнивает каналы."
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
    ("AboutDialog", "Calibration tips"): "Советы по калибровке",
    (
        "AboutDialog",
        "A gamma of 1.0 on a channel is neutral—it does not brighten or darken that primary. "
        "Adjust Red, Green, and Blue when you need to fix a color cast or balance white; "
        "use All when you want one factor applied to every channel. "
        "Small moves and the preview pattern are safer than pushing sliders to extremes.",
    ): (
        "Нейтральная гамма 1.0 по каналу не осветляет и не затемняет этот первичный цвет. "
        "Настраивайте красный, зелёный и синий при цветовом сдвиге или балансе белого; "
        "используйте «Все», когда нужен один множитель для каждого канала. "
        "Небольшие шаги и тестовый шаблон безопаснее, чем увод ползунков в крайние значения."
    ),
    ("SettingsDialog", "Settings"): "Настройки",
    ("SettingsDialog", "About"): "О программе",
    (
        "SettingsDialog",
        "Open version and project information",
    ): "Открыть версию и сведения о проекте",
    ("i18n", "As in system"): "Как в системе",
    ("i18n", "English"): "Английский",
    ("i18n", "Russian"): "Русский",
}


class EmbeddedRussianTranslator(QTranslator):
    """In-process Russian catalog when no .qm is shipped or load fails."""

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if n >= 0:
            return ""
        key = (context, sourceText)
        return _RU.get(key, "")


def read_ui_language_setting() -> str:
    """Return persisted UI language id, or UI_LANGUAGE_SYSTEM if unset (policy 3.11.9)."""
    raw = QSettings().value(SETTINGS_KEY_UI_LANGUAGE, UI_LANGUAGE_SYSTEM)
    if raw is None:
        return UI_LANGUAGE_SYSTEM
    s = str(raw).strip()
    if not s:
        return UI_LANGUAGE_SYSTEM
    return s


def write_ui_language_setting(language_id: str) -> None:
    """Persist UI language (system / en / ru / qm:file.qm)."""
    s = QSettings()
    s.setValue(SETTINGS_KEY_UI_LANGUAGE, language_id)


def _ru_translator_instance() -> QTranslator:
    qm_path = translations_dir() / "xgamma_gui_ru.qm"
    if qm_path.is_file():
        tr_file = QTranslator()
        if tr_file.load(str(qm_path)):
            return tr_file
    return EmbeddedRussianTranslator()


def remove_translators(app) -> None:
    """Remove translators this module installed (for reinstall or shutdown)."""
    installed = getattr(app, _INSTALLED_TRANSLATORS_ATTR, None)
    if not installed:
        return
    for tr in installed:
        app.removeTranslator(tr)
    setattr(app, _INSTALLED_TRANSLATORS_ATTR, [])


def _append_translator(app, tr: QTranslator, bucket: list) -> None:
    app.installTranslator(tr)
    bucket.append(tr)


def _effective_language_id(stored: str) -> str:
    """Resolve UI_LANGUAGE_SYSTEM to en or ru based on locale / LANG."""
    if stored != UI_LANGUAGE_SYSTEM:
        return stored
    return UI_LANGUAGE_RU if want_russian() else UI_LANGUAGE_EN


def _install_for_language_id(app, language_id: str, bucket: list) -> None:
    if language_id == UI_LANGUAGE_EN:
        return
    if language_id == UI_LANGUAGE_RU:
        _append_translator(app, _ru_translator_instance(), bucket)
        return
    if language_id.startswith(QM_LANGUAGE_PREFIX):
        name = language_id[len(QM_LANGUAGE_PREFIX) :]
        if not name or "/" in name or "\\" in name or name.startswith(".."):
            return
        path = translations_dir() / name
        if path.is_file():
            tr_file = QTranslator()
            if tr_file.load(str(path)):
                _append_translator(app, tr_file, bucket)


def install_translators(app) -> None:
    """Install translators before creating UI from QSettings (TASK-015 / PRD 3.11.9, 3.11.12)."""
    remove_translators(app)
    stored = read_ui_language_setting()
    bucket: list = []
    if stored == UI_LANGUAGE_SYSTEM:
        _install_for_language_id(app, _effective_language_id(stored), bucket)
    else:
        _install_for_language_id(app, stored, bucket)
    setattr(app, _INSTALLED_TRANSLATORS_ATTR, bucket)


def reinstall_translators(app) -> None:
    """Re-read settings and replace installed translators (e.g. after changing language)."""
    install_translators(app)


def apply_ui_language(app, main_window) -> None:
    """Reinstall translators from QSettings and refresh main window strings (TASK-016 / PRD 3.11.12)."""
    reinstall_translators(app)
    if main_window is not None:
        main_window.retranslateUi()


def _label_for_extra_qm(path: Path) -> str:
    stem = path.stem
    prefix = "xgamma_gui_"
    code = stem[len(prefix) :] if stem.startswith(prefix) else stem
    if len(code) >= 2:
        loc = QLocale(code)
        native = loc.nativeLanguageName()
        if native:
            return f"{native} ({code})"
    return stem


def iter_ui_language_choices():
    """Yield (language_id, user-visible label) for Settings / menus; includes dynamic .qm (TASK-015)."""
    yield (
        UI_LANGUAGE_SYSTEM,
        QCoreApplication.translate("i18n", "As in system"),
    )
    yield (UI_LANGUAGE_EN, QCoreApplication.translate("i18n", "English"))
    yield (UI_LANGUAGE_RU, QCoreApplication.translate("i18n", "Russian"))
    for path in sorted(translations_dir().glob("*.qm")):
        if path.name.lower() == "xgamma_gui_ru.qm":
            continue
        qid = f"{QM_LANGUAGE_PREFIX}{path.name}"
        yield (qid, _label_for_extra_qm(path))
