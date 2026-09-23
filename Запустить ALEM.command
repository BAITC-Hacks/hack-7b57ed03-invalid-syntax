#!/bin/bash
cd "$(dirname "$0")" || exit 1
for candidate in \
    "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" \
    /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; assert (3,10) <= sys.version_info[:2] < (3,14)' 2>/dev/null; then
        "$candidate" main.py
        result=$?
        if [ "$result" != 0 ]; then
            printf '\nЗапуск не завершён. Нажмите Enter, чтобы закрыть окно.\n'
            read -r
        fi
        exit "$result"
    fi
done
printf 'Нужен Python 3.10–3.13. Установите его с python.org, затем повторите запуск.\n'
read -r
exit 1
