#!/usr/bin/env bash
# exit on error
set -o errexit

STORAGE_DIR=/opt/render/project/.render
mkdir -p $STORAGE_DIR/chrome
mkdir -p $STORAGE_DIR/chromedriver

echo "...Downloading Latest Google Chrome Stable..."
cd $STORAGE_DIR/chrome
wget -q https://google.com
dpkg -x google-chrome-stable_current_amd64.deb .
rm google-chrome-stable_current_amd64.deb

# डाउनलोड किए गए क्रोम का मुख्य वर्जन नंबर पता करना
CHROME_VER=$($STORAGE_DIR/chrome/opt/google/chrome/chrome --version | awk '{print $3}' | cut -d '.' -f 1)
echo "Detected Chrome Version: $CHROME_VER"

echo "...Downloading Matching Chromedriver..."
cd $STORAGE_DIR/chromedriver

# गूगल के नए 'Chrome for Testing' API से वर्जन के हिसाब से ड्राइवर लिंक निकालना
LATEST_DRV_URL="https://googleapis.com{CHROME_VER}.0.6261.94/linux64/chromedriver-linux64.zip"

# यदि ऊपर वाली लिंक में कोई डिफ़ॉल्ट माइनर वर्जन अंतर हो, तो सुरक्षित बैकअप लिंक से डाउनलोड करना
wget -q -O chromedriver.zip "https://gvt1.com" || wget -q -O chromedriver.zip "$LATEST_DRV_URL"

unzip -q chromedriver.zip
mv chromedriver-linux64/chromedriver .
chmod +x chromedriver

# कचरा साफ करना
rm -rf chromedriver.zip chromedriver-linux64

# वापस प्रोजेक्ट रूट में जाना
cd /opt/render/project/src

# पाइथन पैकेज इंस्टॉल करना
pip install -r requirements.txt

echo "...Build Successfully Completed!..."
