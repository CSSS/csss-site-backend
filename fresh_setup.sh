# this is a script for seting up the website from a fresh install

echo "hi sysadmin!"
echo "this script will install everything needed to run the csss website"
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
#sudo apt-get install python3-launchpadlib
sudo apt-get install software-properties-common
#sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
#sudo apt install python3.12 python3.12-venv -y
sudo apt install python3.11 python3.11-venv -y # default on debian 12

echo "installing supervisor & nginx"
sudo apt install supervisor nginx -y

echo "enable & start supervisor"
sudo systemctl enable supervisor
sudo systemctl start supervisor

echo "clone csss-site backend"
cd /home/csss-site
git clone git@github.com:CSSS/csss-site-backend.git

echo "creating a virtual environment for python"
python3.11 -m venv .venv
source .venv/bin/activate

echo "installing pip packages"
cd csss-site-backend
python3.11 -m pip install -r requirements.txt

echo "setup gunicorn (& uvicorn)"
chmod u+x gunicorn_start
pushd src
mkdir run
popd

echo "update ownership for supervisor"
chown csss-site ./src -R
chown csss-site ./gunicorn_start -R
chgrp csss-site ./src -R
chgrp csss-site ./gunicorn_start -R

echo "configure supervisor"
mkdir logs
cp config/supervisor.conf /etc/supervisor/conf.d/csss-site.conf
sudo supervisorctl reread
sudo supervisorctl update

# NOTE: there was some trial & error with these permissions, they may not work first time
echo "configure nginx"
cp config/nginx.conf /etc/nginx/sites-available/csss-site
sudo usermod -aG csss-site www-data
chmod g=rx /home/csss-site/csss-site-backend
chmod g=rwx /home/csss-site/csss-site-backend/src -R
sudo ln -s /etc/nginx/sites-available/csss-site /etc/nginx/sites-enabled/
sudo nginx -t

echo "setup certbot for https"
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx #NOTE: you'll have to fill this out manually: csss-sysadmin@sfu.ca

