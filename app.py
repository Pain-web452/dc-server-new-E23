import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder="templates")

# Meta Graph API version ko environment variable se set kar sakte ho.
# Example: vXX.X
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "vXX.X")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/send-message", methods=["POST"])
def send_message():
    try:
        data = request.get_json(force=True)

        page_access_token = (data.get("pageAccessToken") or "").strip()
        recipient_psid = (data.get("recipientPsid") or "").strip()
        message = (data.get("message") or "").strip()

        if not page_access_token:
            return jsonify({
                "status": "error",
                "message": "Page Access Token missing."
            }), 400

        if not recipient_psid:
            return jsonify({
                "status": "error",
                "message": "Recipient PSID missing."
            }), 400

        if not message:
            return jsonify({
                "status": "error",
                "message": "Message is empty."
            }), 400

        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages"

        payload = {
            "recipient": {
                "id": recipient_psid
            },
            "message": {
                "text": message
            },
            "messaging_type": "RESPONSE"
        }

        response = requests.post(
            url,
            params={
                "access_token": page_access_token
            },
            json=payload,
            timeout=20
        )

        try:
            result = response.json()
        except ValueError:
            result = {
                "raw_response": response.text
            }

        if response.ok:
            return jsonify({
                "status": "success",
                "message": "Message sent successfully.",
                "result": result
            })

        # Meta API ka actual error frontend ko safely return karo.
        error = result.get("error", {})

        return jsonify({
            "status": "error",
            "message": error.get(
                "message",
                f"Meta API returned HTTP {response.status_code}"
            ),
            "code": error.get("code"),
            "type": error.get("type"),
            "error_subcode": error.get("error_subcode"),
            "http_status": response.status_code
        }), response.status_code

    except requests.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Network/API connection error: {str(e)}"
        }), 502

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
