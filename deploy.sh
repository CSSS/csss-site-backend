#!/bin/bash

# NOTE: this script assumes that the local filetree contains what you intend to deploy
# please run the config/update_config.sh if the configuration files are new, or fresh_start.sh if nothing has been installed yet

echo "restarting nginx and gunicorn, gracefully"
sudo systemctl restart nginx
sudo systemctl restart csss-site
