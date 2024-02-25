#!/bin/bash

# TODO:
# - look into `apt install unattended-upgrades`
# - look into activating fail2ban for ssh protection (I doubt we'll need this unless we get too much random traffic)

# this is a script for seting up the website from a fresh install

echo "hi sysadmin!"
echo "this script will install (almost) everything needed to run the csss website"
echo "(make sure you are running on a Debian 12 Linux machine as the superuser!)"

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

echo "----"
echo "configure apt sources..."
echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

echo "----"
echo "update and upgrade apt..."
apt update && apt upgrade -y

echo "----"
echo "install packages..."
apt install git software-properties-common python3.11 python3.11-venv libaugeas0 nginx postgresql-15 postgresql-contrib -y
# install certbot
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install --upgrade pip
/opt/certbot/bin/pip install certbot certbot-nginx
ln -s /opt/certbot/bin/certbot /usr/bin/certbot

echo "----"
echo "add user csss_site..."
useradd csss-site -m # -m: has home /home/csss-site
usermod -L csss-site # -L: cannot login
chsh -s /usr/bin/bash csss-site # make user csss-site use the bash shell
cd /home/csss-site

echo "----"
echo "clone repository csss-site-backend..."
sudo -u csss-site git clone https://github.com/CSSS/csss-site-backend.git csss-site-backend

echo "----"
echo "configure sudo for csss-site..."
cp csss-site-backend/config/sudoers.conf /etc/sudoers.d/csss-site

echo "----"
echo "configure nginx..."
cp csss-site-backend/config/nginx.conf /etc/nginx/sites-available/csss-site-backend
# remove default configuration to prevent funky certbot behaviour
rm /etc/nginx/sites-enabled/default

# prompt user to modify the nginx configuration if they so please
echo "Do you want to modify the nginx configuration file?"
while true; do
	echo "(M)odify, (c)ontinue?"
	read choice

	if [ $choice = 'M' ]; then
		vim /etc/nginx/sites-available/csss-site-backend
	elif [ $choice = 'c' ]; then
		break
	else
		echo "Not sure what you mean..."
	fi
done

echo "You'll need to fill out the certbot configuration manually."
echo "Use csss-sysadmin@sfu.ca for contact email."
certbot --nginx
ln -s /etc/nginx/sites-available/csss-site-backend /etc/nginx/sites-enabled/csss-site-backend
nginx -t

echo "----"
echo "configure www-data user and /var/www..."
usermod -aG www-data csss-site
mkdir /var/www/logs
mkdir /var/www/logs/csss-site-backend
chown -R www-data:www-data /var/www
chmod -R ug=rwx,o=rx /var/www

echo "----"
echo "start nginx..."
systemctl start nginx && systemctl enable nginx

echo "----"
echo "configure postgres..."
# see https://towardsdatascience.com/setting-up-postgresql-in-debian-based-linux-e4985b0b766f for more details
# NOTE: the installation of postgresql-15 creates the postgres user, which has special privileges
sudo -u postgres createdb --no-password main
sudo -u postgres createuser --no-password csss-site
sudo -u postgres psql --command='GRANT ALL PRIVILEGES ON DATABASE main TO "csss-site"'
sudo -u postgres psql main --command='GRANT ALL ON SCHEMA public TO "csss-site"'

echo "----"
echo "create a virtual environment for csss-site..."
sudo -u csss-site python3.11 -m venv .venv
source .venv/bin/activate

echo "----"
echo "install pip packages for csss-site..."
cd csss-site-backend
sudo -u csss-site /home/csss-site/.venv/bin/pip install -r requirements.txt
deactivate

echo "----"
echo "configure csss-site systemd service..."
cp config/csss-site.service /etc/systemd/system/csss-site.service

echo "----"
echo "start csss-site..."
systemctl start csss-site && systemctl enable csss-site

echo "----"
echo "all done."
