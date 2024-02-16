echo "update nginx configs"
cp config/nginx.conf /etc/nginx/sites-available/csss-site
sudo nginx -t
sudo systemctl restart nginx

echo "update supervisor configs (TODO)"
