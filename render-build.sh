#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render

if [ ! -d "$STORAGE_DIR/chrome" ]; then
  echo "...Downloading Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q https://google.com
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm google-chrome-stable_current_amd64.deb
  cd $HOME/project/src # वापस प्रोजेक्ट डायरेक्टरी में आना
else
  echo "...Chrome already installed..."
fi

if [ ! -d "$STORAGE_DIR/chromedriver" ]; then
  echo "...Downloading Chromedriver..."
  mkdir -p $STORAGE_DIR/chromedriver
  cd $STORAGE_DIR/chromedriver
  # लेटेस्ट स्टेबल क्रोमड्राइवर डाउनलोड करना
  wget -q https://googleapis.com
  unzip chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 zip chromedriver-linux64.zip
  chmod +x chromedriver
  cd $HOME/project/src
else
  echo "...Chromedriver already installed..."
fi

# पाइथन पैकेज इंस्टॉल करना
pip install -r requirements.txt
