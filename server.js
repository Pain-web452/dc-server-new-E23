const express = require('express');
const puppeteer = require('puppeteer');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// मुख्य पेज (HTML फ़्रंटएंड दिखाना)
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// जब यूजर "START TASK" बटन दबाएगा
app.post('/start-task', upload.single('messageFile'), async (req, res) => {
    const { e2eePin, messagePrefix, delaySeconds, fbEmail, fbPassword, targetUrl } = req.body;
    
    if (!req.file) {
        return res.status(400).send("❌ कृपया .txt फाइल अपलोड करें!");
    }

    if (!fbEmail || !fbPassword || !targetUrl) {
        return res.status(400).send("❌ फेसबुक ईमेल, पासवर्ड और टारगेट लिंक ज़रूरी हैं!");
    }

    const filePath = req.file.path;
    const delayTime = parseInt(delaySeconds) || 120;

    // फाइल से मैसेजेस पढ़ना
    const fileContent = fs.readFileSync(filePath, 'utf-8');
    let messages = fileContent.split('\n').map(line => line.trim()).filter(line => line.length > 0);

    // अगर प्रीफिक्स (Prefix) दिया है तो मैसेज के आगे जोड़ना
    if (messagePrefix) {
        messages = messages.map(msg => `${messagePrefix} ${msg}`);
    }

    // यूजर को तुरंत रिस्पॉन्स भेजना ताकि पेज हैंग न हो
    res.send("🚀 आपका टास्क बैकग्राउंड में शुरू हो चुका है! सर्वर लॉग्स (Render Logs) चेक करें।");

    // बैकग्राउंड में बोट प्रोसेस शुरू करना
    runMessengerBot(fbEmail, fbPassword, targetUrl, messages, delayTime, filePath);
});

async function runMessengerBot(email, password, targetUrl, messages, delayTime, tempFilePath) {
    console.log("🤖 मैसेंजर बोट लॉन्च हो रहा है...");
    
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-notifications']
    });

    const page = await browser.newPage();

    try {
        // 1. फेसबुक लॉगिन
        console.log("🔐 फेसबुक लॉगिन कर रहा हूँ...");
        await page.goto('https://facebook.com', { waitUntil: 'networkidle2' });
        await page.type('#email', email);
        await page.type('#pass', password);
        await page.click('[name="login"]');
        await new Promise(res => setTimeout(res, 6000));

        // 2. चैट लिंक ओपन करना
        console.log("📬 इनबॉक्स चैट ओपन की जा रही है...");
        await page.goto(targetUrl, { waitUntil: 'networkidle2' });
        await new Promise(res => setTimeout(res, 5000));

        // 3. एक-एक करके मैसेज भेजना
        for (let i = 0; i < messages.length; i++) {
            const selector = 'div[role="textbox"][contenteditable="true"]';
            await page.waitForSelector(selector, { timeout: 15000 });
            
            await page.type(selector, messages[i]);
            await page.keyboard.press('Enter');
            
            console.log(`✅ भेजा गया [${i + 1}/${messages.length}]: ${messages[i]}`);
            
            if (i < messages.length - 1) {
                console.log(`⏳ अगले मैसेज के लिए ${delayTime} सेकंड रुक रहे हैं...`);
                await new Promise(res => setTimeout(res, delayTime * 1000));
            }
        }
    } catch (err) {
        console.log(`❌ एरर आया: ${err.message}`);
    } finally {
        console.log("🏁 टास्क पूरा हुआ। ब्राउज़र बंद हो रहा है।");
        await browser.close();
        if (fs.existsSync(tempFilePath)) fs.unlinkSync(tempFilePath); // टेम्परेरी फाइल डिलीट करना
    }
}

app.listen(PORT, () => {
    console.log(`🚀 सर्वर पोर्ट ${PORT} पर चल रहा है`);
});
