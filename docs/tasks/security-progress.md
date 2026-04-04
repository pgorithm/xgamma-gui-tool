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
