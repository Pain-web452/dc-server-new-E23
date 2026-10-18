const express = require("express");
const fs = require("fs");
const path = require("path");
const pino = require("pino");
const multer = require("multer");
const {
  default: Gifted_Tech,
  useMultiFileAuthState,
  delay,
  makeCacheableSignalKeyStore,
  Browsers,
} = require("maher-zubair-baileys");

const app = express();
const PORT = process.env.PORT || 5000;

if (!fs.existsSync("sessions")) fs.mkdirSync("sessions");
if (!fs.existsSync("uploads")) fs.mkdirSync("uploads");

const upload = multer({ dest: "uploads/" });
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static("public"));

const activeSessions = new Map();
const serverStartTime = Date.now();
let globalLogs = [
    { time: new Date().toLocaleTimeString(), message: "Server started – PETER WP SERVER" }
];

function addLog(msg) {
    const timeStr = new Date().toLocaleTimeString();
    globalLogs.unshift({ time: timeStr, message: msg });
    if (globalLogs.length > 50) globalLogs.pop();
}

// Neon Red Cyberpunk Theme HTML Template
const htmlTemplate = (activeTab, bodyContent) => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PETER WP SERVER D</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0d0208;
            --card-bg: #1a030d;
            --primary: #ff0055;
            --secondary: #ff3366;
            --text-light: #f8f9fa;
            --border-color: #3b071a;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-light);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }
        .container { max-width: 950px; }
        header {
            text-align: center;
            margin-bottom: 25px;
            padding: 15px;
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 0 15px rgba(255, 0, 85, 0.2);
        }
        header h1 {
            color: var(--primary);
            font-weight: 800;
            font-size: 1.5rem;
            letter-spacing: 1px;
            margin: 0;
            text-shadow: 0 0 8px rgba(255, 0, 85, 0.4);
        }
        .nav-tabs-custom {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
        }
        .nav-btn {
            flex: 1;
            padding: 12px;
            text-align: center;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-light);
            border-radius: 8px;
            font-weight: bold;
            text-decoration: none;
            text-transform: uppercase;
            transition: all 0.3s;
        }
        .nav-btn.active, .nav-btn:hover {
            background: var(--primary);
            color: #000;
            box-shadow: 0 0 12px var(--primary);
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.6);
        }
        .card h2 {
            color: var(--primary);
            font-size: 1.2rem;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }
        label { font-weight: 600; color: #d8b4c2; font-size: 0.9rem; margin-bottom: 5px; }
        input, select, textarea {
            background-color: #0d0208 !important;
            border: 1px solid var(--border-color) !important;
            color: #fff !important;
            border-radius: 6px !important;
            padding: 10px !important;
            font-size: 0.95rem;
        }
        input:focus { border-color: var(--primary) !important; box-shadow: 0 0 8px rgba(255, 0, 85, 0.4) !important; }
        button, .btn-custom {
            background: var(--primary);
            border: none;
            color: #fff;
            font-weight: bold;
            text-transform: uppercase;
            padding: 10px;
            border-radius: 6px;
            width: 100%;
            transition: all 0.3s;
        }
        button:hover, .btn-custom:hover {
            opacity: 0.9;
            box-shadow: 0 0 12px var(--primary);
            color: #fff;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background: #0d0208;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-box h4 { font-size: 0.8rem; color: #aaa; margin-bottom: 5px; text-transform: uppercase; }
        .stat-box .val { font-size: 1.4rem; font-weight: bold; color: var(--primary); }
        .terminal-box {
            background: #050103;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px;
            font-family: monospace;
            font-size: 12px;
            height: 220px;
            overflow-y: auto;
            color: #00ff66;
        }
        .log-line { margin-bottom: 4px; border-bottom: 1px solid #110207; padding-bottom: 2px; }
        .log-time { color: var(--primary); margin-right: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>PETER WP SERVER D</h1>
            <p class="text-muted small mb-0">Multi-Session WhatsApp Control Center</p>
        </header>

        <div class="nav-tabs-custom">
            <a href="/" class="nav-btn ${activeTab === 'dashboard' ? 'active' : ''}">Dashboard</a>
            <a href="/bulk" class="nav-btn ${activeTab === 'bulk' ? 'active' : ''}">Bulk Sender</a>
        </div>

        ${bodyContent}
    </div>
</body>
</html>
`;

// Dashboard Route
app.get("/", (req, res) => {
    let totalSessions = activeSessions.size;
    let pairedCount = Array.from(activeSessions.values()).filter(s => s.status === "Connected").length;
    
    let uptimeSec = Math.floor((Date.now() - serverStartTime) / 1000);
    let hrs = String(Math.floor(uptimeSec / 3600)).padStart(2, '0');
    let mins = String(Math.floor((uptimeSec % 3600) / 60)).padStart(2, '0');
    let secs = String(uptimeSec % 60).padStart(2, '0');
    let uptimeStr = `${hrs}:${mins}:${secs}`;

    let pairedListHtml = Array.from(activeSessions.entries()).map(([id, sess]) => `
        <div class="d-flex justify-content-between align-items-center p-2 mb-2 bg-black rounded border border-secondary">
            <div>
                <strong>Session: ${id}</strong> | Number: ${sess.number}
                <br><small class="text-success">Status: ${sess.status}</small>
            </div>
            <form action="/delete-session" method="POST" class="m-0">
                <input type="hidden" name="sessionId" value="${id}">
                <button type="submit" class="btn btn-sm btn-danger py-1 px-2" style="width:auto;">Delete</button>
            </form>
        </div>
    `).join('') || '<p class="text-muted small text-center mb-0">No sessions yet. Add a number above.</p>';

    let logsHtml = globalLogs.map(l => `
        <div class="log-line"><span class="log-time">[${l.time}]</span> ${l.message}</div>
    `).join('');

    const content = `
        <div class="card">
            <h2>➕ Add WhatsApp Number</h2>
            <form action="/add-session" method="POST">
                <div class="mb-3">
                    <label>Session ID (1, 2, 3...)</label>
                    <input type="text" name="sessionId" placeholder="e.g. 1" required>
                    <small class="text-muted">Har number ka alag session ID</small>
                </div>
                <div class="mb-3">
                    <label>Phone Number (Country Code, no + or spaces)</label>
                    <input type="text" name="number" placeholder="e.g. 919876543210" required>
                </div>
                <button type="submit">Get Pairing Code</button>
            </form>
        </div>

        <div class="card">
            <h2>📱 Paired Numbers</h2>
            ${pairedListHtml}
        </div>

        <div class="card">
            <h2>📊 Live Stats</h2>
            <div class="stats-grid">
                <div class="stat-box">
                    <h4>Total Sessions</h4>
                    <div class="val">${totalSessions}</div>
                </div>
                <div class="stat-box">
                    <h4>Paired</h4>
                    <div class="val">${pairedCount}</div>
                </div>
                <div class="stat-box">
                    <h4>Uptime</h4>
                    <div class="val" style="font-size:1.1rem;">${uptimeStr}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h2 class="mb-0">🖥️ Live Log</h2>
                <form action="/clear-logs" method="POST" class="m-0">
                    <button type="submit" class="btn btn-sm btn-outline-danger py-0 px-2" style="font-size:11px; width:auto;">Clear Log</button>
                </form>
            </div>
            <div class="terminal-box">
                ${logsHtml}
            </div>
        </div>
    `;

    res.send(htmlTemplate('dashboard', content));
});

// Bulk Sender Tab Route
app.get("/bulk", (req, res) => {
    const sessionOpts = Array.from(activeSessions.keys()).map(id => `<option value="${id}">Session ID: ${id}</option>`).join('') || '<option value="">No Active Sessions</option>';
    
    const content = `
        <div class="card">
            <h2>🚀 Bulk Message Sender</h2>
            <form action="/send-bulk" method="POST" enctype="multipart/form-data">
                <div class="mb-3">
                    <label>Select Session ID</label>
                    <select name="sessionId" required>${sessionOpts}</select>
                </div>
                <div class="mb-3">
                    <label>Target Group/Number JID</label>
                    <input type="text" name="target" placeholder="1234567890@s.whatsapp.net or groupJID@g.us" required>
                </div>
                <div class="mb-3">
                    <label>Upload Message File (.txt)</label>
                    <input type="file" name="messageFile" accept=".txt" required>
                </div>
                <div class="mb-3">
                    <label>Delay (Seconds)</label>
                    <input type="number" name="delaySec" value="5" min="1" required>
                </div>
                <button type="submit">Start Bulk Sending</button>
            </form>
        </div>
    `;
    res.send(htmlTemplate('bulk', content));
});

// Add Session / Get Pairing Code Endpoint
app.post("/add-session", async (req, res) => {
    const { sessionId, number } = req.body;
    if (!sessionId || !number) return res.redirect("/");

    const cleanNumber = number.replace(/[^0-9]/g, "");
    const sessionPath = path.join("sessions", `session_${sessionId}`);

    if (!fs.existsSync(sessionPath)) fs.mkdirSync(sessionPath, { recursive: true });

    try {
        const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
        const logger = pino({ level: "fatal" }).child({ level: "fatal" });

        const client = Gifted_Tech({
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger),
            },
            printQRInTerminal: false,
            logger: logger,
            browser: Browsers.macOS("Desktop"),
        });

        activeSessions.set(sessionId, {
            client,
            number: cleanNumber,
            status: "Initializing",
            path: sessionPath
        });

        client.ev.on("creds.update", saveCreds);

        client.ev.on("connection.update", async (update) => {
            const { connection } = update;
            if (connection === "open") {
                activeSessions.get(sessionId).status = "Connected";
                addLog(`Session ${sessionId} (${cleanNumber}) connected successfully!`);
            } else if (connection === "close") {
                activeSessions.get(sessionId).status = "Disconnected";
                addLog(`Session ${sessionId} connection closed.`);
            }
        });

        if (!client.authState.creds.registered) {
            await delay(4000);
            let code = await client.requestPairingCode(cleanNumber);
            code = code ? code.match(/.{1,4}/g)?.join("-") || code : "FAILED";
            addLog(`Pairing code generated for session ${sessionId}`);

            return res.send(htmlTemplate('dashboard', `
                <div class="card text-center">
                    <h2>Pairing Code for Session ${sessionId}</h2>
                    <div style="font-size: 28px; letter-spacing: 2px; margin: 20px 0; padding: 20px; background: #050103; border: 2px dashed var(--primary); border-radius: 10px; color: var(--primary);">
                        <strong>${code}</strong>
                    </div>
                    <p>Number: ${cleanNumber}</p>
                    <p class="text-muted">Enter this code on your WhatsApp linked devices.</p>
                    <a href="/" class="btn-custom" style="display:inline-block; text-decoration:none; padding:10px 20px;">Return to Dashboard</a>
                </div>
            `));
        }

        res.redirect("/");
    } catch (error) {
        addLog(`Error in session ${sessionId}: ${error.message}`);
        res.redirect("/");
    }
});

// Clear Logs Endpoint
app.post("/clear-logs", (req, res) => {
    globalLogs = [{ time: new Date().toLocaleTimeString(), message: "Logs cleared by user." }];
    res.redirect("/");
});

// Delete Session Endpoint
app.post("/delete-session", async (req, res) => {
    const { sessionId } = req.body;
    if (activeSessions.has(sessionId)) {
        try {
            const sess = activeSessions.get(sessionId);
            await sess.client?.ws?.close();
            if (fs.existsSync(sess.path)) {
                fs.rmSync(sess.path, { recursive: true, force: true });
            }
            activeSessions.delete(sessionId);
            addLog(`Session ${sessionId} deleted.`);
        } catch (e) {
            console.error(e);
        }
    }
    res.redirect("/");
});

app.listen(PORT, () => {
    console.log(`PETER WP SERVER running on port ${PORT}`);
});
