# This script adds commands to the current crontab

# run the daily script at 1am every morning
# TODO: make sure timezone is PST
crontab -l | { cat; echo "0 1 * * * /home/csss-site/csss-site-backend/src/cron/daily.py"; } | crontab -

