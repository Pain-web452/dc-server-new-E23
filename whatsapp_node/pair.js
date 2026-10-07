const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');

async function getPairingCode(phoneNumber) {
    try {
        // Auth state save karne ke liye
        const { state, saveCreds } = await useMultiFileAuthState('auth_info');

        const sock = makeWASocket({
            auth: state,
            printQRInTerminal: false,
            logger: pino({ level: 'silent' }),
            browser: ['Ubuntu', 'Chrome', '20.0.04']
        });

        // Credentials save karo
        sock.ev.on('creds.update', saveCreds);

        // Agar already registered nahi hai toh pairing code maango
        if (!sock.authState.creds.registered) {
            // Thoda wait karo connection ke liye
            await new Promise(resolve => setTimeout(resolve, 3000));

            const code = await sock.requestPairingCode(phoneNumber);
            
            // JSON output print karo
            console.log(JSON.stringify({ code: code }));
            
            // Process exit karo
            process.exit(0);
        } else {
            console.log(JSON.stringify({ code: "ALREADY_CONNECTED" }));
            process.exit(0);
        }

    } catch (error) {
        console.error(JSON.stringify({ error: error.message }));
        process.exit(1);
    }
}

// Command line se phone number lo
const phoneNumber = process.argv[2];

if (!phoneNumber) {
    console.log(JSON.stringify({ error: "Phone number required" }));
    process.exit(1);
}

getPairingCode(phoneNumber);
