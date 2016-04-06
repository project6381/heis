COMEDI_VERSION="comedilib-0.10.2"

echo "Installing" $COMEDI_VERSION

wget http://comedi.org:8000/download/comedilib-0.10.2.tar.gz
tar -xzf $COMEDI_VERSION.tar.gz
rm $COMEDI_VERSION.tar.gz
cd $COMEDI_VERSION
./configure --with-udev-hotplug=/lib --sysconfdir=/etc
make
sudo make install
cd ..

echo -e "\n\n\n___________\nInstall successful!"