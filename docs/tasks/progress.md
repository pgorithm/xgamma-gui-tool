# Progress

- **TASK-001 (2026-04-04):** Ошибки `applyGamma` (отложенное применение и Reset) показываются в статусной строке; полный вывод последнего apply хранится в `GammaCore.lastApplyRawOutput` / `getLastApplyRawOutput()`. Ручная проверка сбоя xgamma — под Linux/X11.
- **TASK-002 (2026-04-04):** `ConfigManager.saveToAutostart` / `removeFromAutostart` возвращают результат с краткой причиной для статусной строки; полный traceback и путь — в лог (`logging`). Reset удаляет только `xgamma_gui_tool.desktop` (PRD 3.6). Ручная проверка отказа записи в autostart — под Linux/X11.
