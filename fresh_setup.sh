#!/bin/bash

# TODO:
# - look into `apt install unattended-upgrades`
# - look into activating fail2ban for ssh protection (I doubt we'll need this unless we get too much random traffic)

# this is a script for seting up the website from a fresh install

echo "hi sysadmin!"
echo "this script will install (almost) everything needed to run the csss website"
echo "(make sure you are running on a Debian 12 Linux machine as the superuser!)"
echo "==="

# ask the user for consent to proceed
while true; do
	echo "(P)roceed, (c)ancel?"
	read choice

	if [ $choice = 'P' ]; then
		break
	elif [ $choice = 'c' ]; then
		exit 0
	else
		echo "Not sure what you mean..."
	fi
done

echo "configure apt sources..."
echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

echo "update and upgrade apt..."
apt update && apt upgrade -y

echo "install packages..."
apt install git software-properties-common python3.11 python3.11-venv libaugeas0 nginx postgresql-15 postgresql-contrib -y
# install certbot
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install --upgrade pip
/opt/certbot/bin/pip install certbot certbot-nginx
ln -s /opt/certbot/bin/certbot /usr/bin/certbot

echo "add user csss_site..."
useradd csss-site -m # -m: has home /home/csss-site
usermod -L csss-site # -L: cannot login

echo "clone repository csss-site-backend..."
sudo -u csss-site git clone git@github.com:CSSS/csss-site-backend.git /home/csss-site

echo "configure sudo for csss-site..."
cp /home/csss-site/csss-site-backend/config/sudoers.conf /etc/sudoers.d/csss-site

echo "configure nginx..."
cp /home/csss-site/csss-site-backend/config/nginx.conf /etc/nginx/sites-available/csss-site
ln -s /etc/nginx/sites-available/csss-site /etc/nginx/sites-enabled/
echo "You'll need to fill out the certbot configuration manually."
echo "Use csss-sysadmin@sfu.ca for contact email."
certbot --nginx
nginx -t

echo "configure www-data user and /var/www..."
usermod -aG www-data csss-site
chown -R www-data:www-data /var/www
chmod -R ug=rwx,o=rx /var/www

echo "start nginx..."
systemctl start nginx && systemctl enable nginx

echo "configure postgres..."
# see https://towardsdatascience.com/setting-up-postgresql-in-debian-based-linux-e4985b0b766f for more details
# NOTE: the installation of postgresql-15 creates the postgres user, which has special privileges
sudo -u postgres createdb --no-password main
sudo -u postgres createuser --no-password csss-site
sudo -u postgres psql --command='GRANT ALL PRIVILEGES ON DATABASE main TO "csss-site"'
sudo -u postgres psql main --command='GRANT ALL ON SCHEMA public TO "csss-site"'

echo "login to csss-site..."
su csss-site
# (csss-site)
cd /home/csss-site

echo "create a virtual environment for csss-site..."
python3.11 -m venv .venv
source .venv/bin/activate

echo "install pip packages for csss-site..."
cd csss-site-backend
sudo -u csss-site python3.11 -m pip install -r requirements.txt
deactivate

echo "logout from csss-site..."
exit
# (root)

echo "configure csss-site systemd service..."
cp /home/csss-site/csss-site-backend/config/csss-site.service /etc/systemd/system/csss-site.service

echo "start csss-site..."
systemctl start csss-site && systemctl enable csss-site
