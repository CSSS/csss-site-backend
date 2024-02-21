#!/bin/bash

# this is a script for seting up the website from a fresh install

echo "hi sysadmin!"
echo "this script will install (almost) everything needed to run the csss website"
echo "==="

echo "update apt to latest packages..."
sudo apt update && sudo apt upgrade -y

# TODO: look into `sudo apt install unattended-upgrades`
# TODO: look into activating fail2ban for ssh protection (I doubt we'll need this unless we get too much random traffic)

echo "installing git..."
sudo apt install git

echo "creating csss_site user account..."
sudo useradd csss-site -m # has home
sudo usermod -L csss-site # cannot login

echo "installing python3.12"
sudo apt-get install software-properties-common
sudo apt update
sudo apt install python3.11 python3.11-venv -y # default on debian 12

echo "installing supervisor & nginx"
sudo apt install nginx -y
#chmod g=rwx /home/csss-site/csss-site-backend/src -R

echo "clone csss-site backend"
cd /home/csss-site
git clone git@github.com:CSSS/csss-site-backend.git

echo "creating a virtual environment for python"
python3.11 -m venv .venv
source .venv/bin/activate

echo "installing pip packages"
cd csss-site-backend
#sudo apt install swig gcc-11
python3.11 -m pip install -r requirements.txt

echo "setup gunicorn (& uvicorn)"
cd src
mkdir run
cd .. 

echo "update ownership"
chown csss-site:csss-site ./src -R
chown csss-site:csss-site ./gunicorn_start.sh -R

echo "setup csss-site systemd service"
cp config/csss-site.service /etc/systemd/system/csss-site.service
systemctl start csss-site
systemctl enable csss-site

echo "setup sudo access to nginx and csss-site"
cp config/sudoers.conf /etc/sudoers.d/csss-site

# NOTE: there was some trial & error with these permissions, they may not work first time
echo "configure nginx"
cp config/nginx.conf /etc/nginx/sites-available/csss-site
sudo usermod -aG csss-site www-data
sudo usermod -aG www-data csss-site
sudo chown www-data:www-data /var/www
sudo chmod g=rwx /var/www/html
sudo chmod g=rwx /var/www/
sudo ln -s /etc/nginx/sites-available/csss-site /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "setup certbot for https"
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx #NOTE: you'll have to fill this out manually: csss-sysadmin@sfu.ca

echo "install postgres"
# get the official apt repository
# see https://www.postgresql.org/download/linux/debian/ for more details
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install postgresql-15 postgresql-contrib

echo "update postgres config"
# see https://towardsdatascience.com/setting-up-postgresql-in-debian-based-linux-e4985b0b766f for more details
sudo -i -u postgres
createdb --no-password main
createuser --no-password csss-site
psql --command='GRANT ALL PRIVILEGES ON DATABASE main TO "csss-site"'
psql main --command='GRANT ALL ON SCHEMA public TO "csss-site"'

# NOTE: file permissions during this setup process needs some work

