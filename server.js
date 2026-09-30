const express = require('express');
const login = require('fca-unofficial');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname)));

const activeBotSessions = {};

// कुकी को सही तरीके से कन्वर्ट करने और डोमेन फिक्स करने का फंक्शन
function parseCookieToAppState(cookieStr) {
    const appState = [];
    const pairs = cookieStr.split(';');
    pairs.forEach(pair => {
        const parts = pair.split('=');
        if (parts.length >= 2) {
            const key = parts[0].trim();
            const value = parts.slice(1).join('=').trim();
            
            // मैसेंजर लॉगिन के लिए .facebook.com डोमेन होना ज़रूरी है
            appState.push({
                key: key,
                value: value,
                domain: "facebook.com",
                path: "/",
                hostOnly: false,
                creation: new Date().toISOString(),
                lastAccessed: new Date().toISOString()
            });
        }
    });
    return appState;
}

app.post('/api/start-messenger', (req, res) => {
    const { cookie, targetId, pin, prefix, messages, delay } = req.body;
    
    if (!cookie || !targetId) {
        return res.status(400).json({ success: false, message: "Cookie and Target ID are required!" });
    }

    const appState = parseCookieToAppState(cookie);
    const taskId = Math.random().toString(36).substring(7);
    let msgIndex = 0;

    // फेसबुक सिक्योरिटी को बाईपास करने के लिए रियल मोबाइल एजेंट कॉन्फ़िगरेशन
    const loginOptions = {
        appState: appState,
        userAgent: "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
    };

    login(loginOptions, (err, api) => {
        if (err) {
            console.error("FCA Login Detail Error:", err);
            
            // यूजर को साफ शब्दों में एरर बताना
            let errorMsg = "Invalid Cookie or Checkpoint Triggered.";
            if (err.error === "login-approval") {
                errorMsg = "Checkpoint Triggered! Please approve login from your FB App.";
            } else if (err.error === "wrong-password") {
                errorMsg = "Cookie session has expired. Please grab a new cookie.";
            }
            
            return res.status(500).json({ success: false, message: errorMsg, details: err });
        }

        // E2EE पिन और आवश्यक सेटिंग्स
        api.setOptions({
            listenEvents: false,
            selfListen: false,
            forceLogin: true,
            userAgent: "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        });

        console.log(`[${taskId}] Bot logged in successfully!`);

        const timerId = setInterval(() => {
            if (messages.length === 0) return;
            
            let rawMessage = messages[msgIndex];
            let finalMessage = prefix ? `${prefix} ${rawMessage}` : rawMessage;

            api.sendMessage(finalMessage, targetId, (msgErr) => {
                if (msgErr) {
                    console.log(`[${taskId}] Message Delivery Failed:`, msgErr);
                } else {
                    console.log(`[${taskId}] Sent to IB: "${finalMessage}"`);
                }
            });

            msgIndex = (msgIndex + 1) % messages.length;
        }, delay);

        activeBotSessions[taskId] = { timerId, api };
        res.json({ success: true, taskId });
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
