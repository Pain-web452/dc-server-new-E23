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

if (!fs.existsSync("temp")) fs.mkdirSync("temp");
if (!fs.existsSync("uploads")) fs.mkdirSync("uploads");

const upload = multer({ dest: "uploads/" });
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static("public"));

const activeSessions = new Map();

const htmlTemplate = (additionalContent = "") => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ WhatsApp Automation Bot Panel ⚡</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: #121826;
            --primary: #00ff66;
            --secondary: #00bcd4;
            --text-light: #e0e0e0;
            --border-color: #1f293d;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-light);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
        }
        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #121826, #1a233a);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 0 20px rgba(0, 255, 102, 0.1);
        }
        header h1 {
            color: var(--primary);
            font-weight: 800;
            text-shadow: 0 0 10px rgba(0, 255, 102, 0.3);
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        .card h2 {
            color: var(--secondary);
            font-size: 1.4rem;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }
        label {
            font-weight: 600;
            color: #b0bec5;
            margin-bottom: 6px;
        }
        input, select, textarea {
            background-color: #0b0f19 !important;
            border: 1px solid #2a3b5c !important;
            color: #fff !important;
            border-radius: 8px !important;
            padding: 12px !important;
        }
        input:focus, select:focus, textarea:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 8px rgba(0, 255, 102, 0.3) !important;
        }
        button, .btn-custom {
            background: linear-gradient(135deg, #00ff66, #00bcd4);
            border: none;
            color: #000;
            font-weight: bold;
            text-transform: uppercase;
            padding: 12px;
            border-radius: 8px;
            width: 100%;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        button:hover, .btn-custom:hover {
            opacity: 0.9;
            transform: translateY(-2px);
            box-shadow: 0 0 15px rgba(0, 255, 102, 0.4);
            color: #000;
        }
        .btn-danger {
            background: linear-gradient(135deg, #ff4b2b, #ff416c) !important;
            color: #fff !important;
        }
        .btn-secondary {
            background: #2a3b5c !important;
            color: #fff !important;
        }
        .session-item {
            background: #1a233a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .message-log {
            max-height: 200px;
            overflow-y: auto;
            background: #0b0f19;
            border: 1px solid var(--border-color);
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            margin-top: 10px;
        }
        .log-entry {
            border-bottom: 1px solid #1f293d;
            padding: 4px 0;
        }
        .status-connected { color: #00ff66; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ WHATSAPP AUTOMATION BOT ⚡</h1>
            <p class="text-muted mb-0">Secure Pairing, Group Selection & Multi-Session Sender</p>
        </header>
        ${additionalContent}
    </div>
</body>
</html>
`;

// Home route with pre-filled target support
app.get("/", (req, res) => {
    const prefillTarget = req.query.target || "";
    const prefillSession = req.query.taskId || "";

    const sessionListHtml = Array.from(activeSessions.entries()).map(([id, session]) => `
        <div class="session-item">
            <div class="session-info" style="flex: 1; min-width: 250px;">
                <h3>${session.name} (ID: <code>${id}</code>)</h3>
                <p class="mb-1">Number: ${session.number}</p>
                <p class="mb-1">Status: <span class="status-connected">Connected</span></p>
                <a href="/fetch-groups?taskId=${id}" class="btn btn-sm btn-secondary mt-2 mb-2" style="width: auto; padding: 5px 15px; font-size: 12px;">📁 Fetch Joined Groups</a>
                <div class="message-log">
                    ${session.logs.slice(-5).map(log => `
                        <div class="log-entry">
                            <span class="log-time">${new Date(log.time).toLocaleTimeString()}</span>
                            <span class="log-message">${log.message}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="session-actions">
                <form action="/stop-session" method="POST">
                    <input type="hidden" name="taskId" value="${id}">
                    <button type="submit" class="btn btn-danger btn-sm">Stop Session</button>
                </form>
            </div>
        </div>
    `).join('') || '<p class="text-muted">No active sessions running.</p>';

    const content = `
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <h2>Generate Pairing Code</h2>
                    <form action="/code" method="GET">
                        <div class="form-group mb-3">
                            <label for="number">WhatsApp Number</label>
                            <input type="text" id="number" name="number" placeholder="e.g. 919876543210" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="sessionName">Session Name (Optional)</label>
                            <input type="text" id="sessionName" name="sessionName" placeholder="My Bot Session">
                        </div>
                        <button type="submit">Generate Code</button>
                    </form>
                </div>
            </div>
            
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <h2>Send Messages</h2>
                    <form action="/send-message" method="POST" enctype="multipart/form-data">
                        <div class="form-group mb-3">
                            <label for="taskId">Session/Task ID</label>
                            <input type="text" id="taskId" name="taskId" value="${prefillSession}" placeholder="Enter session ID" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="targetType">Target Type</label>
                            <select id="targetType" name="targetType" required>
                                <option value="group" ${prefillTarget ? 'selected' : ''}>Group ID</option>
                                <option value="number">Phone Number</option>
                            </select>
                        </div>
                        <div class="form-group mb-3">
                            <label for="target">Target (Number / Group ID)</label>
                            <input type="text" id="target" name="target" value="${prefillTarget}" placeholder="Recipient number or group JID" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="messageFile">Message File (.txt)</label>
                            <input type="file" id="messageFile" name="messageFile" accept=".txt" required>
                        </div>
                        <div class="form-group mb-3">
                            <label for="delaySec">Delay (Seconds)</label>
                            <input type="number" id="delaySec" name="delaySec" min="1" value="5" required>
                        </div>
                        <button type="submit">Start Sending</button>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="card session-list">
            <h2>Active Sessions</h2>
            ${sessionListHtml}
        </div>
    `;
    
    res.send(htmlTemplate(content));
});

// Pairing code route
app.get("/code", async (req, res) => {
    const { number, sessionName } = req.query;
    if (!number) {
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Phone number is required.</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }

    const taskId = Math.random().toString(36).substring(2, 10);
    const tempPath = path.join("temp", taskId);

    if (!fs.existsSync(tempPath)) {
        fs.mkdirSync(tempPath, { recursive: true });
    }

    const cleanNumber = number.replace(/[^0-9]/g, "");
    
    try {
        const { state, saveCreds } = await useMultiFileAuthState(tempPath);
        const logger = pino({ level: "fatal" }).child({ level: "fatal" });
        
        const client = Gifted_Tech({
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger),
            },
            printQRInTerminal: false,
            logger: logger,
            browser: Browsers.ubuntu("Chrome"),
        });

        const sName = sessionName ? sessionName : "Session " + taskId;

        activeSessions.set(taskId, {
            client,
            number: cleanNumber,
            name: sName,
            path: tempPath,
            logs: [],
            saveCreds,
            state,
            running: true
        });
        
        activeSessions.get(taskId).log = (message) => {
            const entry = { time: Date.now(), message: message };
            activeSessions.get(taskId).logs.push(entry);
            console.log(`[${taskId}] ${message}`);
        };

        client.ev.on("creds.update", saveCreds);
        
        client.ev.on("connection.update", async (update) => {
            const { connection, lastDisconnect } = update;
            if (connection === "open") {
                activeSessions.get(taskId)?.log("WhatsApp connected successfully");
            } else if (connection === "close") {
                if (lastDisconnect?.error?.output?.statusCode !== 401) {
                    activeSessions.get(taskId)?.log("Connection lost, reconnecting...");
                    await delay(10000);
                    initializeClient(taskId);
                } else {
                    activeSessions.get(taskId)?.log("Session terminated - authentication error");
                    activeSessions.delete(taskId);
                }
            }
        });

        if (!client.authState.creds.registered) {
            await delay(4000);
            let code = await client.requestPairingCode(cleanNumber);
            code = code ? code.match(/.{1,4}/g)?.join("-") || code : "FAILED";

            return res.send(htmlTemplate(`
                <div class="card text-center">
                    <h2>Pairing Code Generated</h2>
                    <div style="font-size: 28px; letter-spacing: 2px; margin: 20px 0; padding: 20px; background: #0b0f19; border: 2px dashed var(--primary); border-radius: 10px; color: var(--primary);">
                        <strong>${code}</strong>
                    </div>
                    <p>Task ID: <code>${taskId}</code></p>
                    <p>Number: ${cleanNumber}</p>
                    <p class="text-muted">Enter this code in your WhatsApp linked devices.</p>
                    <a href="/" class="btn-custom mt-3">Return to Dashboard</a>
                </div>
            `));
        } else {
            return res.send(htmlTemplate(`
                <div class="card text-center">
                    <h2>Session Info</h2>
                    <p>This number is already registered.</p>
                    <p>Task ID: <code>${taskId}</code></p>
                    <a href="/" class="btn-custom mt-3">Return to Dashboard</a>
                </div>
            `));
        }
    } catch (error) {
        console.error("Error generating pairing code:", error);
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Failed to generate pairing code: ${error.message}</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }
});

// Group Fetch Route with direct message action button
app.get("/fetch-groups", async (req, res) => {
    const { taskId } = req.query;
    if (!taskId || !activeSessions.has(taskId)) {
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Invalid or inactive Session ID.</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }

    const session = activeSessions.get(taskId);
    try {
        const groups = await session.client.groupFetchAllParticipating();
        let groupRows = "";
        for (let gId in groups) {
            const group = groups[gId];
            groupRows += `
                <tr>
                    <td style="color:var(--primary); font-weight:600;">${group.subject}</td>
                    <td><code>${gId}</code></td>
                    <td>
                        <a href="/?taskId=${taskId}&target=${gId}" class="btn btn-sm" style="background:#00ff66; color:#000; font-weight:bold; padding:5px 12px; border-radius:5px; text-decoration:none;">🚀 Select & Send Msg</a>
                    </td>
                </tr>`;
        }

        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Joined Groups (${Object.keys(groups).length})</h2>
                <div class="table-responsive">
                    <table class="table table-dark table-striped align-middle">
                        <thead>
                            <tr>
                                <th>Group Name</th>
                                <th>Group JID</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${groupRows || '<tr><td colspan="3" class="text-center">No groups found</td></tr>'}
                        </tbody>
                    </table>
                </div>
                <a href="/" class="btn-custom mt-3">Back to Dashboard</a>
            </div>
        `));
    } catch (error) {
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error Fetching Groups</h2>
                <p>${error.message}</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }
});

async function initializeClient(taskId) {
    if (!activeSessions.has(taskId)) return;
    const session = activeSessions.get(taskId);
    
    try {
        const { state, saveCreds } = await useMultiFileAuthState(session.path);
        const logger = pino({ level: "fatal" }).child({ level: "fatal" });
        
        session.client = Gifted_Tech({
            auth: {
                creds: state.creds,
                keys: makeCacheableSignalKeyStore(state.keys, logger),
            },
            printQRInTerminal: false,
            logger: logger,
            browser: Browsers.ubuntu("Chrome"),
        });

        session.client.ev.on("creds.update", saveCreds);
        
        session.client.ev.on("connection.update", async (update) => {
            const { connection, lastDisconnect } = update;
            if (connection === "open") {
                session.log("Reconnected successfully");
            } else if (connection === "close") {
                if (lastDisconnect?.error?.output?.statusCode !== 401) {
                    session.log("Reconnection failed, trying again...");
                    await delay(15000);
                    initializeClient(taskId);
                } else {
                    session.log("Session terminated - authentication error");
                    activeSessions.delete(taskId);
                }
            }
        });
    } catch (error) {
        session.log(`Reconnection error: ${error.message}`);
        await delay(30000);
        initializeClient(taskId);
    }
}

app.post("/send-message", upload.single("messageFile"), async (req, res) => {
    const { taskId, target, targetType, delaySec } = req.body;
    const filePath = req.file?.path;

    if (!taskId || !target || !filePath || !delaySec) {
        if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Missing required fields.</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }

    if (!activeSessions.has(taskId)) {
        if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Invalid session ID or session not active.</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }

    const session = activeSessions.get(taskId);
    
    try {
        const messages = fs.readFileSync(filePath, "utf-8")
            .split("\n")
            .filter(msg => msg.trim() !== "");
        
        if (messages.length === 0) {
            return res.send(htmlTemplate(`
                <div class="card text-center">
                    <h2>Error</h2>
                    <p>Message file is empty.</p>
                    <a href="/" class="btn-custom mt-3">Go Back</a>
                </div>
            `));
        }

        const recipient = targetType === "group" ? target : target + "@s.whatsapp.net";
        let index = 0;
        
        session.log(`Started sending messages to ${target}`);
        
        (async () => {
            while (session.running && activeSessions.has(taskId)) {
                if (index >= messages.length) index = 0;
                const msg = messages[index];
                
                try {
                    await session.client.sendMessage(recipient, { text: msg });
                    session.log(`Sent to ${target}: ${msg.substring(0, 40)}...`);
                } catch (error) {
                    session.log(`Error sending message: ${error.message}`);
                    await delay(5000);
                    index++;
                    continue;
                }
                
                index++;
                await delay(parseInt(delaySec) * 1000);
            }
        })();

        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Message Sending Started</h2>
                <p>Messages are now being sent to <code>${target}</code> (${targetType})</p>
                <a href="/" class="btn-custom mt-3">Return to Dashboard</a>
            </div>
        `));
    } catch (error) {
        session.log(`Error in message sending: ${error.message}`);
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Failed to start message sending: ${error.message}</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    } finally {
        if (filePath && fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
    }
});

app.post("/stop-session", async (req, res) => {
    const { taskId } = req.body;
    if (!taskId || !activeSessions.has(taskId)) {
        return res.send(htmlTemplate(`
            <div class="card text-center">
                <h2>Error</h2>
                <p>Invalid session ID.</p>
                <a href="/" class="btn-custom mt-3">Go Back</a>
            </div>
        `));
    }
    
    const session = activeSessions.get(taskId);
    session.running = false;
    
    try {
        await session.client?.ws?.close();
        session.log("Session stopped by user");
    } catch (error) {
        console.error("Error stopping session:", error);
    }
    
    activeSessions.delete(taskId);
    
    return res.send(htmlTemplate(`
        <div class="card text-center">
            <h2>Session Stopped</h2>
            <p>Session ${taskId} has been stopped.</p>
            <a href="/" class="btn-custom mt-3">Return to Dashboard</a>
        </div>
    `));
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});