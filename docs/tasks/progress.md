# Progress

- **TASK-001 (2026-04-04):** Ошибки `applyGamma` (отложенное применение и Reset) показываются в статусной строке; полный вывод последнего apply хранится в `GammaCore.lastApplyRawOutput` / `getLastApplyRawOutput()`. Ручная проверка сбоя xgamma — под Linux/X11.
- **TASK-002 (2026-04-04):** `ConfigManager.saveToAutostart` / `removeFromAutostart` возвращают результат с краткой причиной для статусной строки; полный traceback и путь — в лог (`logging`). Reset удаляет только `xgamma_gui_tool.desktop` (PRD 3.6). Ручная проверка отказа записи в autostart — под Linux/X11.
- **TASK-003 (2026-04-04):** После инициализации в статусе больше не показывается сырой многострочный вывод xgamma; для успешного чтения — «Ready», для xrandr/сбоя — короткие сообщения, диагностика в лог. `py -m compileall` ок; полные шаги 2–3 — вручную под X11.
- **TASK-004 (2026-04-04):** До `InitializationWorker` слайдеры/поля ввода/Reset/Apply отключены, в полях placeholder «…», превью — «Reading display gamma…», статус — «Loading initial settings…»; после `finished` — реальные значения и включение контролов. `py -m compileall` ок; шаги 2–3 под X11.
