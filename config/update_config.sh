#!/bin/bash

# make sure user is root
user=$(whoami)
if [ $user != 'root' ]; then
	echo "this script must be run as the superuser."
	exit 1
fi

echo "1. update nginx configs"
cp /home/csss-site/csss-site-backend/config/nginx.conf /etc/nginx/sites-available/csss-site
certbot --nginx # reconfigure the server with SSL certificates
nginx -t
# only restart nginx if config is valid
if [ $? -eq 0 ]; then
	systemctl restart nginx
fi

echo "2. update csss-site service config"
systemd-analyze verify /home/csss-site/csss-site-backend/config/csss-site.service
# only use new service if it is valid
if [ $? -eq 0 ]; then
	cp /home/csss-site/csss-site-backend/config/csss-site.service /etc/systemd/system/csss-site.service
	systemctl restart csss-site
fi

echo "3. update sudo config"
cp /home/csss-site/csss-site-backend/config/sudoers.conf /etc/sudoers.d/csss-site
