Translations for xgamma GUI Tool (Qt .qm)

Shipped catalog: embedded Russian in src/i18n.py (EmbeddedRussianTranslator) when
xgamma_gui_ru.qm is absent. Optional file xgamma_gui_ru.qm in this directory
overrides embedded strings if present.

For maintainers / translators (.ts → .qm):

1. Install Qt linguist tools (e.g. Debian/Ubuntu: qttools5-dev-tools).
2. From the repository root, extract strings into a .ts file (adjust paths if needed):
     pylupdate5 src/gui.py src/main.py src/i18n.py -ts src/translations/xgamma_gui_ru.ts
3. Edit xgamma_gui_ru.ts with Qt Linguist (or by hand).
4. Compile:
     lrelease src/translations/xgamma_gui_ru.ts -qm src/translations/xgamma_gui_ru.qm
5. Commit both .ts and .qm; keep src/i18n.py _RU dict in sync or rely on .qm only.

Runtime: Russian UI when the system locale or LANG/LC_* is Russian (e.g. LANG=ru_RU.UTF-8).
