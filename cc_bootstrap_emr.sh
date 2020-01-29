#!/bin/bash

sudo apt-get install -y git
sudo apt-get install libgeoip-dev 
sudo pip install geoip2
sudo pip install boto
sudo pip install warc
sudo pip install https://github.com/commoncrawl/gzipstream/archive/master.zip

echo '# database credential:' >> .bashrc
echo "export POSTGRES_PASSWORD='postgres_password'" >> .bashrc
echo "export POSTGRES_USER='postgres_user'" >> .bashrc
echo "export POSTGRES_LOCATION='postgres_private_ip'" >> .bashrc

echo "database credential bootstrap" > bootstrap.txt
echo `date` >> bootstrap.txt
source .bashrc

