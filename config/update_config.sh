#!/bin/bash

echo "1. update nginx configs"
cp /home/csss-site/csss-site-backend/config/nginx.conf /etc/nginx/sites-available/csss-site
sudo nginx -t
sudo systemctl restart nginx

echo "2. update csss-site service config"
sudo systemd-analyze verify /home/csss-site/csss-site-backend/config/csss-site.service
cp /home/csss-site/csss-site-backend/config/csss-site.service /etc/systemd/system/csss-site.service
sudo systemctl restart csss-site

