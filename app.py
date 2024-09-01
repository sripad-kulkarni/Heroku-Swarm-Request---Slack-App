from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os

# Initialize the Bolt app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Handle the slash command
@app.command("/swarmrequest")
def handle_swarm_request(ack, body, client):
    # Acknowledge the command request
    ack()

    # Open a modal with fields for the swarm request
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "swarm_request_form",
            "title": {"type": "plain_text", "text": "Create Swarm Request"},
            "submit": {"type": "plain_text", "text": "Submit"},  # Add this line
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "ticket",
                    "element": {"type": "plain_text_input", "action_id": "ticket_input"},
                    "label": {"type": "plain_text", "text": "Ticket"}
                },
                {
                    "type": "input",
                    "block_id": "entitlement",
                    "element": {
                        "type": "static_select",
                        "action_id": "entitlement_select",
                        "placeholder": {"type": "plain_text", "text": "Select Entitlement"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Enterprise Signature"}, "value": "enterprise_signature"},
                            {"text": {"type": "plain_text", "text": "Enterprise Premier"}, "value": "enterprise_premier"},
                            {"text": {"type": "plain_text", "text": "Enterprise Standard"}, "value": "enterprise_standard"},
                            {"text": {"type": "plain_text", "text": "Online Customer"}, "value": "online_customer"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Entitlement"}
                },
                # Add other input fields here...
            ]
        }
    )

if __name__ == "__main__":
    # Initialize the Socket Mode handler to listen for events
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
