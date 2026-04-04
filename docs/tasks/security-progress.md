# Security audit progress (RALPH cycle)

## [SEC-001] PATH: подмена xgamma / xrandr / systemd-detect-virt
**Дата:** 2026-04-04
**Vuln ref:** 1.1
**Статус:** partially
**Вердикт:** `xgamma` резолвится через `shutil.which('xgamma')`, и именно этот путь передаётся первым аргументом в `subprocess.run` — выполняется первый одноимённый бинарь в PATH. `xrandr` и `systemd-detect-virt` вызываются списком с неполным именем (`xrandr`, `systemd-detect-virt`), поэтому ОС также ищет их по PATH. Это стандартная модель для переносимости, но при каталоге раньше системного в PATH возможна подмена исполняемого файла в контексте пользователя.

**Что проверено:**
- Файлы: `src/gamma_core.py`, `src/environment_checks.py`
- Сценарий: чтение кода + pytest с моками `shutil.which` / `subprocess.run` + AST по спискам argv для `subprocess.run`

**Результат:**
- `GammaCore._findXgamma` → `shutil.which('xgamma')`; `applyGamma` / `getCurrentGamma` / `buildXgammaCommand` используют `self.xgammaPath`.
- `_readGammaFromXrandr`: `['xrandr', '--verbose']`.
- `EnvironmentProbe`: `['systemd-detect-virt']`, `['xrandr', '--verbose']`.

**PoC / тест:** `tests/security/test_sec_001.py`
**Автотест:** `tests/security/test_sec_001.py` (`@pytest.mark.security`)

**Рекомендации по исправлению:**
- По желанию ужесточить политику: после `which` проверять, что путь входит в доверенный префикс (например `/usr/bin`, `/bin`) или сравнивать с `os.path.realpath` известных кандидатов; документировать риск PATH для пользователей.
- Для `xrandr` / `systemd-detect-virt` — аналогично либо фиксированные абсолютные пути там, где это приемлемо для целевых дистрибутивов.

**Предложения на будущее:**
- Упомянуть в README для параноиков: не добавлять в PATH непроверенные каталоги с приоритетом выше системных.

---

## [SEC-002] Инъекция через оболочку (shell=True, небезопасная склейка)
**Дата:** 2026-04-04
**Vuln ref:** 1.2
**Статус:** not_exploitable
**Вердикт:** Во всех целевых модулях внешние команды вызываются через `subprocess.run` со списком argv; `shell=True`, строковая форма argv и `os.system` отсутствуют. Числовые параметры гаммы передаются как `str(float)` в отдельные аргументы, не через оболочку.

**Что проверено:**
- Файлы: `src/gamma_core.py`, `src/environment_checks.py`, `src/gui.py`, `src/main.py`
- Сценарий: статический разбор AST + ручной обзор вызовов `subprocess`

**Результат:**
- `gamma_core`: `[self.xgammaPath]` и список `args` для apply; `xrandr` — `['xrandr', '--verbose']`
- `environment_checks`: `['systemd-detect-virt']`, `['xrandr', '--verbose']`
- `gui.py`, `main.py`: вызовов `subprocess` нет

**PoC / тест:** `tests/security/test_sec_002.py`
**Автотест:** `tests/security/test_sec_002.py` (`@pytest.mark.security`)

**Рекомендации по исправлению:**
- Не требуется для данного вектора; сохранять политику: только argv-list, без `shell=True`.

**Предложения на будущее:**
- Отдельно оценить строку `Exec=` в `.desktop` (склейка в `buildXgammaCommand`) на предмет кавычек/пробелов в пути к `xgamma` — это смежный, не subprocess-shell вектор (см. задачи про автозапуск/PATH).

---

## [SEC-006] Путь автозапуска: только XDG и фиксированное имя файла
**Дата:** 2026-04-04
**Vuln ref:** 2.1
**Статус:** config_dependent
**Вердикт:** Каталог и имя файла заданы в коде как `Path.home() / '.config' / 'autostart'` и литерал `xgamma_gui_tool.desktop` — произвольная подстановка пути из пользовательского ввода отсутствует. Базовый каталог дома берётся из `Path.home()` (на Unix — `HOME`, на Windows — в том числе `USERPROFILE`), поэтому при подмене этих переменных до запуска процесса запись уйдёт в иной корень, чем «реальный» дом пользователя. Переменная `XDG_CONFIG_HOME` не используется: при нестандартном XDG каталог автозапуска приложения может не совпадать с каталогом, который ожидает окружение рабочего стола.

**Что проверено:**
- Файлы: `src/config_manager.py`
- Сценарий: чтение кода + дочерний процесс с заданными `HOME`/`USERPROFILE` и `XDG_CONFIG_HOME` + статическая проверка исходника (нет `getenv`, нет `XDG_CONFIG_HOME`)

**Результат:**
- `AUTOSTART_DIR` / `DESKTOP_FILE` — атрибуты класса от `Path.home()` и фиксированных сегментов; имя `.desktop` не параметризуется.

**PoC / тест:** `tests/security/test_sec_006.py`
**Автотест:** `tests/security/test_sec_006.py` (`@pytest.mark.security`)

**Рекомендации по исправлению:**
- По желанию: для Linux учитывать `XDG_CONFIG_HOME` при выборе базы (`Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))` с нормализацией и валидацией), документировать зависимость от `HOME`/`USERPROFILE`.

**Предложения на будущее:**
- В README кратко указать, что автозапуск пишется в `$HOME/.config/autostart` (и эквивалент на Windows через профиль), а не в произвольный путь из UI.

---

## [SEC-016] Зависимости requirements.txt: известные CVE и pinning
**Дата:** 2026-04-04
**Vuln ref:** 5.1
**Статус:** not_exploitable
**Вердикт:** На дату проверки `pip-audit` (PyPI/OSV) для дерева, разрешённого из `requirements.txt`, не сообщил известных уязвимостей (пример разрешения: `pyqt5` 5.15.11, `pyqt5-qt5` 5.15.2, `pyqt5-sip` 12.18.0). В файле указан только нижний предел `PyQt5>=5.12.0` без верхней границы и без lock-файла — воспроизводимость установки и соответствие будущим CVE зависят от политики обновлений и окружения pip.

**Что проверено:**
- Файлы: `requirements.txt`
- Сценарий: `python -m pip_audit -r requirements.txt --format json` + pytest в `tests/security/test_sec_016.py`

**Результат:**
- Единственная прямая зависимость: `PyQt5>=5.12.0`; транзитивные пакеты — `pyqt5-qt5`, `pyqt5-sip`.
- Актуальная база advisories на момент прогона: пустой список `vulns` для всех зависимостей в JSON-выводе.

**PoC / тест:** `tests/security/test_sec_016.py`
**Автотест:** `tests/security/test_sec_016.py` (`@pytest.mark.security`; второй тест пропускается, если не установлен пакет `pip-audit`)

**Рекомендации по исправлению:**
- Для воспроизводимых сборок и CI: зафиксировать точные версии (`==`) или ввести `requirements.lock` / `pip-tools` / аналог.
- Периодически повторять `pip-audit` при обновлении зависимостей.

**Предложения на будущее:**
- Опционально добавить `pip-audit` в dev-зависимости или отдельный workflow, чтобы второй тест не пропускался в автоматике.

---
