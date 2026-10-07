from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

# ... aapka baaki code ...

@app.route('/get-pairing-code', methods=['POST'])
def get_pairing_code():
    try:
        data = request.get_json()
        phone_number = data.get('phone')

        if not phone_number:
            return jsonify({"success": False, "error": "Phone number required"})

        # Yahan aapko Node.js script call karni padegi jo pairing code generate karegi
        # Neeche wala command example hai (aapke whatsapp_node folder ke hisaab se badalna padega)
        
        # Maan lijiye aapke paas 'whatsapp_node/pair.js' file hai
        result = subprocess.run(
            ['node', 'whatsapp_node/pair.js', phone_number],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Node script output se code nikalna hoga (JSON format mein)
            output = json.loads(result.stdout)
            return jsonify({"success": True, "code": output.get("code")})
        else:
            return jsonify({"success": False, "error": result.stderr})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run()
