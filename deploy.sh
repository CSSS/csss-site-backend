#!/bin/bash

echo "getting new changes from git"
git fetch
git pull

echo "restarting gunicorn, gracefully"
sudo systemctl restart nginx
sudo systemctl restart csss-site
