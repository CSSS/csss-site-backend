#!/bin/sh

# Install the weekly TransLink static schedule refresh without duplicating it.
set -eu

cron_file=$(mktemp)
trap 'rm -f "$cron_file"' EXIT

crontab -l 2>/dev/null | sed \
    -e '/# BEGIN CSSS TRANSLINK STATIC/,/# END CSSS TRANSLINK STATIC/d' \
    -e '\|scripts.refresh_translink_static|d' > "$cron_file" || true

{
    cat "$cron_file"
    printf '%s\n' \
        '# BEGIN CSSS TRANSLINK STATIC' \
        'PATH=/home/csss-site/.local/bin:/usr/local/bin:/usr/bin:/bin' \
        'CRON_TZ=America/Vancouver' \
        '0 23 * * 5 cd /home/csss-site/csss-site-backend/src && uv run python -m scripts.refresh_translink_static' \
        '# END CSSS TRANSLINK STATIC'
} | crontab -
