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
const PORT = 5000;

// Create necessary directories
if (!fs.existsSync("temp")) fs.mkdirSync("temp");
if (!fs.existsSync("uploads")) fs.mkdirSync("uploads");

const upload = multer({ dest: "uploads/" });
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static("public"));

// Store active sessions
const activeSessions = new Map();

// Improved UI HTML
const htmlTemplate = (additionalContent = "") => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Multi-User Sender</title>
    <style>
        :root {
            --primary: #25D366;
            --secondary: #128C7E;
            --accent: #34B7F1;
            --light: #f5f5f5;
            --dark: #075E54;
            --danger: #dc3545;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--secondary), var(--dark));
            color: white;
            padding: 20px 0;
            text-align: center;
            border-radius: 8px 8px 0 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        h1, h2, h3 {
            margin-bottom: 15px;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--dark);
        }
        
        input, select, button, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            border-color: var(--accent);
            outline: none;
            box-shadow: 0 0 0 3px rgba(52, 183, 241, 0.2);
        }
        
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        button:hover {
            background-color: var(--secondary);
        }
        
        .btn-danger {
            background-color: var(--danger);
        }
        
        .btn-danger:hover {
            background-color: #c82333;
        }
        
        .session-list {
            margin-top: 30px;
        }
        
        .session-item {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session-info {
            flex: 1;
        }
        
        .session-actions {
            margin-left: 15px;
        }
        
        .status-connected {
            color: var(--primary);
            font-weight: bold;
        }
        
        .status-disconnected {
            color: var(--danger);
            font-weight: bold;
        }
        
        .message-log {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 6px;
            background-color: #f9f9f9;
            margin-top: 10px;
        }
        
        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            border-bottom: 1px solid #eee;
        }
        
        .log-time {
            color: #666;
            font-size: 12px;
            margin-right: 10px;
        }
        
        .log-message {
            color: #333;
        }
        
        .flex-container {
            display: flex;
            gap: 20px;
        }
        
        .flex-item {
            flex: 1;
        }
        
        @media (max-width: 768px) {
            .flex-container {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WhatsApp Multi-User Message Sender</h1>
            <p>Send messages to multiple recipients with individual sessions</p>
        </header>
        
        ${additionalContent}
    </div>
</body>
</html>
`;

// Home route
app.get("/", (req, res) => {
    const content = `
        <div class="flex-container">
            <div class="flex-item">
                <div class="card">
                    <h2>Create New Session</h2>
                    <form action="/code" method="GET">
                        <div class="form-group">
                            <label for="number">WhatsApp Number</label>
                            <input type="text" id="number" name="number" placeholder="e.g. 919876543210" required>
                        </div>
                        <div class="form-group">
                            <label for="sessionName">Session Name (Optional)</label>
                            <input type="text" id="sessionName" name="sessionName" placeholder="My Business Account">
                        </div>
                        <button type="submit">Generate Pairing Code</button>
                    </form>
                </div>
            </div>
            
            <div class="flex-item">
                <div class="card">
                    <h2>Send Messages</h2>
                    <form action="/send-message" method="POST" enctype="multipart/form-data">
                        <div class="form-group">
                            <label for="taskId">Session/Task ID</label>
                            <input type="text" id="taskId" name="taskId" placeholder="Enter your session ID" required>
                        </div>
                        <div class="form-group">
                            <label for="targetType">Target Type</label>
                            <select id="targetType" name="targetType" required>
                                <option value="">-- Select Target Type --</option>
                                <option value="number">Phone Number</option>
                                <option value="group">Group ID</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="target">Target</label>
                            <input type="text" id="target" name="target" placeholder="Phone number or Group ID" required>
                        </div>
                        <div class="form-group">
                            <label for="messageFile">Message File (TXT)</label>
                            <input type="file" id="messageFile" name="messageFile" accept=".txt" required>
                        </div>
                        <div class="form-group">
                            <label for="delaySec">Delay Between Messages (seconds)</label>
                            <input type="number" id="delaySec" name="delaySec" min="1" value="5" required>
                        </div>
                        <button type="submit">Start Sending</button>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="card session-list">
            <h2>Active Sessions</h2>
            ${Array.from(activeSessions.entries()).map(([id, session]) => `
                <div class="session-item">
                    <div class="session-info">
                        <h3>${session.name || 'Unnamed Session'} (ID: ${id})</h3>
                        <p>Number: ${session.number}</p>
                        <p>Status: <span class="status-connected">Connected</span></p>
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
                        <form action="/stop-session" method="POST" style="margin-bottom: 10px;">
                            <input type="hidden" name="taskId" value="${id}">
                            <button type="submit" class="btn-danger">Stop Session</button>
                        </form>
                    </div>
                </div>
            `).join('') || '<p>No active sessions</p>'}
        </div>
    `;
    
    res.send(htmlTemplate(content));
});

// Generate pairing code
app.get("/code", async (req, res) => {
    const { number, sessionName } = req.query;
    if (!number) {
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Phone number is required</p>
                <a href="/">Go back</a>
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

        if (!client.authState.creds.registered) {
            await delay(1500);
            const code = await client.requestPairingCode(cleanNumber);
            
            // Create new session
            activeSessions.set(taskId, {
                client,
                number: cleanNumber,
                name: sessionName || `Session ${taskId}`,
                path: tempPath,
                logs: [],
                saveCreds,
                state,
                running: true
            });
            
            // Add log function to session
            activeSessions.get(taskId).log = (message) => {
                const entry = {
                    time: Date.now(),
                    message: message
                };
                activeSessions.get(taskId).logs.push(entry);
                console.log(`[${taskId}] ${message}`);
            };

            client.ev.on("creds.update", saveCreds);
            
            client.ev.on("connection.update", async (update) => {
                const { connection, lastDisconnect } = update;
                
                if (connection === "open") {
                    activeSessions.get(taskId).log("WhatsApp connected successfully");
                    await delay(2000);
                } 
                else if (connection === "close") {
                    if (lastDisconnect?.error?.output?.statusCode !== 401) {
                        activeSessions.get(taskId).log("Connection lost, reconnecting...");
                        await delay(10000);
                        initializeClient(taskId);
                    } else {
                        activeSessions.get(taskId).log("Session terminated - authentication error");
                        activeSessions.delete(taskId);
                    }
                }
            });

            return res.send(htmlTemplate(`
                <div class="card">
                    <h2>Pairing Code Generated</h2>
                    <div style="font-size: 24px; margin: 20px 0; padding: 15px; background: #f0f8ff; border-radius: 5px;">
                        Your Pairing Code: <strong>${code}</strong>
                    </div>
                    <p>Task ID: <code>${taskId}</code> (Save this to control your session)</p>
                    <p>Number: ${cleanNumber}</p>
                    <p>Session will automatically connect once paired.</p>
                    <a href="/" class="btn">Return to Dashboard</a>
                </div>
            `));
        }
    } catch (error) {
        console.error("Error generating pairing code:", error);
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Failed to generate pairing code: ${error.message}</p>
                <a href="/">Go back</a>
            </div>
        `));
    }
});

// Initialize client (for reconnections)
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
            } 
            else if (connection === "close") {
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

// Send messages
app.post("/send-message", upload.single("messageFile"), async (req, res) => {
    const { taskId, target, targetType, delaySec } = req.body;
    const filePath = req.file?.path;

    if (!taskId || !target || !filePath || !delaySec) {
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Missing required fields</p>
                <a href="/">Go back</a>
            </div>
        `));
    }

    if (!activeSessions.has(taskId)) {
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Invalid session ID or session not active</p>
                <a href="/">Go back</a>
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
                <div class="card">
                    <h2>Error</h2>
                    <p>Message file is empty</p>
                    <a href="/">Go back</a>
                </div>
            `));
        }

        const recipient = targetType === "group" ? target + "@g.us" : target + "@s.whatsapp.net";
        let index = 0;
        
        session.log(`Started sending messages to ${recipient}`);
        
        // Start sending in background
        (async () => {
            while (session.running) {
                const msg = messages[index];
                
                try {
                    await session.client.sendMessage(recipient, { text: msg });
                    session.log(`Sent to ${target}: ${msg.substring(0, 50)}${msg.length > 50 ? '...' : ''}`);
                } catch (error) {
                    session.log(`Error sending message: ${error.message}`);
                    await delay(5000);
                    continue;
                }
                
                index = (index + 1) % messages.length;
                await delay(parseInt(delaySec) * 1000);
            }
        })();

        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Message Sending Started</h2>
                <p>Messages are now being sent to ${target} (${targetType})</p>
                <p>Delay: ${delaySec} seconds between messages</p>
                <p>Total messages: ${messages.length}</p>
                <p>Task ID: <code>${taskId}</code></p>
                <div class="message-log">
                    ${session.logs.slice(-5).map(log => `
                        <div class="log-entry">
                            <span class="log-time">${new Date(log.time).toLocaleTimeString()}</span>
                            <span class="log-message">${log.message}</span>
                        </div>
                    `).join('')}
                </div>
                <a href="/">Return to Dashboard</a>
            </div>
        `));
    } catch (error) {
        session.log(`Error in message sending: ${error.message}`);
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Failed to start message sending: ${error.message}</p>
                <a href="/">Go back</a>
            </div>
        `));
    } finally {
        if (filePath && fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }
    }
});

// Stop session
app.post("/stop-session", async (req, res) => {
    const { taskId } = req.body;
    
    if (!taskId || !activeSessions.has(taskId)) {
        return res.send(htmlTemplate(`
            <div class="card">
                <h2>Error</h2>
                <p>Invalid session ID</p>
                <a href="/">Go back</a>
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
        <div class="card">
            <h2>Session Stopped</h2>
            <p>Session ${taskId} has been stopped</p>
            <a href="/">Return to Dashboard</a>
        </div>
    `));
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
