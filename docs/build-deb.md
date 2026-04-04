# Сборка .deb из репозитория

Кратко: на Debian/Ubuntu из корня клона репозитория достаточно установить пакеты для сборки и вызвать `dpkg-buildpackage`. В GitHub пакет собирается workflow при **публикации** релиза.

## Локальная сборка

1. Установите зависимости для сборки (тот же набор, что в [`.github/workflows/build-deb.yml`](../.github/workflows/build-deb.yml)):

   ```bash
   sudo apt update
   sudo apt install -y build-essential debhelper dh-python python3-all \
     python3-setuptools fakeroot devscripts
   ```

2. Перейдите в корень репозитория (где лежит каталог `debian/`) и соберите бинарный пакет без подписи:

   ```bash
   dpkg-buildpackage -us -uc -b -jauto
   ```

3. Файл `.deb` появится в **родительском** каталоге относительно корня репозитория, имя вида `xgamma-gui-tool_<версия>_all.deb`.

Версия берётся из первой строки [`debian/changelog`](../debian/changelog) (формат Debian: `пакет (версия-ревизия) дистрибутив; urgency=…`).

`requirements.txt` должен быть в репозитории и закоммичен — иначе падает CI-сборка (см. [docs/new-agents.md](new-agents.md)).

## Сборка в GitHub

Файл workflow: [`.github/workflows/build-deb.yml`](../.github/workflows/build-deb.yml), имя в интерфейсе: **Build DEB package**.

### Когда запускается

- Событие **Release → published**: релиз переведён из черновика в опубликованный **или** создан сразу как опубликованный.
- Тип **`created`** в workflow не используется: сборка не стартует при сохранении **черновика** релиза — только после публикации.
- Отмеченный как **pre-release** релиз тоже даёт событие `published`, workflow выполнится и прикрепит артефакты (как для обычного релиза).

### Что сделать вручную

1. Закоммитьте в `main` (или в ту ветку, из которой делаете релиз) всё нужное для сборки: `debian/`, `src/`, `main.py`, `requirements.txt` и т.д.
2. На GitHub: **Releases → Draft a new release** (или **Choose a tag** для нового тега).
3. Укажите **tag** (например `v1.0.1` или `1.0.1`). Из имени тега в версию пакета берётся строка **без** ведущего `v`: `v1.0.1` → `1.0.1`.
4. Опубликуйте релиз (**Publish release**). После этого в **Actions** появится запуск **Build DEB package**.

### Что делает job

Кратко: ставит зависимости Debian и `pip install -r requirements.txt`, копирует дерево в `deb_build/`, подставляет версию из тега в первую строку `debian/changelog` и в `src/version_info.py`, запускает `dpkg-buildpackage -us -uc -b -jauto`, затем загружает файлы к этому релизу.

### Артефакты на релизе

- бинарный пакет `xgamma-gui-tool_…_all.deb`;
- `SHA256SUMS` для проверки целостности скачанного `.deb`.

Для загрузки используется `GITHUB_TOKEN` с правом `contents: write` (задано в workflow).
