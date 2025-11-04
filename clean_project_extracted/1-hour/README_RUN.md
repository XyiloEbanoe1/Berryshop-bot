Как запускать бота локально

Скрипты находятся в каталоге `scripts/` в корне репозитория.

1) Запуск (одной командой):

```bash
# из корня репозитория
scripts/start-bot.sh
```

Это:
- использует Python из `./.venv/bin/python`, если виртуальное окружение создано в корне;
- запускает `main.py` из `clean_project_extracted/1-hour`;
- создаёт `run/bot.pid` с PID процесса и лог `logs/bot.log`.

2) Остановка (одной командой):

```bash
scripts/stop-bot.sh
```

Скрипт сначала пытается корректно завершить процесс по PID, найденному в `run/bot.pid`, затем при необходимости делает принудительное убийство. Если PID-файла нет, он попробует поискать процесс по пути `main.py`.

3) Быстрая проверка состояния:

```bash
pgrep -af '/workspaces/Berryshop-bot/clean_project_extracted/1-hour/main.py' || echo 'no processes'
```

4) Логи и PID:
- Логи: `clean_project_extracted/1-hour/logs/bot.log`
- PID: `clean_project_extracted/1-hour/run/bot.pid`

Безопасность:
- Убедитесь, что в `.env` нет публичных токенов при публикации репозитория. Для разработки используйте локальный `.env` с placeholder-значениями.
