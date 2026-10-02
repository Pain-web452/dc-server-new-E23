#!/usr/bin/env bash
# exit on error
set -o errexit

# पाइथन पैकेज इंस्टॉल करना
pip install -r requirements.txt

# Render सर्वर के अंदर बिना किसी एरर के क्रोमियम ब्राउज़र इंस्टॉल करना
playwright install chromium
