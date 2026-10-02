# पाइथन के ऑफिशियल स्टेबल लिनक्स बेस इमेज का उपयोग
FROM python:3.10-slim

# आवश्यक लिनक्स पैकेज और गूगल क्रोम इंस्टॉल करना
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://google.com | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://google.com stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# प्रोजेक्ट डायरेक्टरी सेट करना
WORKDIR /app

# डिपेंडेंसी इंस्टॉल करना
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# बाकी का पूरा कोड कॉपी करना
COPY . .

# पोर्ट को ओपन करना
EXPOSE 5000

# Gunicorn के जरिए Flask ऐप को स्टार्ट करना
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
