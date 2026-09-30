const express = require('express');
const login = require('fca-unofficial');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname)));

const activeBotSessions = {};

function parseCookieToAppState(cookieStr) {
    const appState = [];
    const pairs = cookieStr.split(';');
    pairs.forEach(pair => {
        const parts = pair.split('=');
        if (parts.length >= 2) {
            const key = parts[0].trim();
            const value = parts.slice(1).join('=').trim();
            appState.push({
                key: key,
                value: value,
                domain: "facebook.com",
                path: "/"
            });
        }
    });
    return appState;
}

app.post('/api/start-messenger', (req, res) => {
    const { cookie, targetId, pin, prefix, messages, delay } = req.body;
    const appState = parseCookieToAppState(cookie);
    const taskId = Math.random().toString(36).substring(7);
    let msgIndex = 0;

    login({ appState: appState }, (err, api) => {
        if (err) {
            console.error(err);
            return res.status(500).json({ success: false, message: "Invalid Cookie or Checkpoint Triggered." });
        }

        // E2EE सेटिंग्स कॉन्फ़िगरेशन
        if (pin && typeof api.setOptions === 'function') {
            api.setOptions({ listenEvents: true, selfListen: false, forceLogin: true });
        }

        console.log(`[${taskId}] Bot authenticated and ready for IB messages.`);

        const timerId = setInterval(() => {
            if (messages.length === 0) return;
            
            let rawMessage = messages[msgIndex];
            let finalMessage = prefix ? `${prefix} ${rawMessage}` : rawMessage;

            api.sendMessage(finalMessage, targetId, (msgErr) => {
                if (msgErr) {
                    console.log(`[${taskId}] Send Error to ID ${targetId}:`, msgErr);
                } else {
                    console.log(`[${taskId}] Message sent to IB: "${finalMessage}"`);
                }
            });

            msgIndex = (msgIndex + 1) % messages.length;
        }, delay);

        activeBotSessions[taskId] = { timerId, api };
        res.json({ success: true, taskId });
    });
});

// Render के पोर्ट डायनामिक्स को संभालने के लिए संपादन
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
