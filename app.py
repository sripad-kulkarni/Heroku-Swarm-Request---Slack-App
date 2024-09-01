import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
)

# Handle the slash command to open a modal
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
            "blocks": [
                {"type": "input", "block_id": "ticket", "element": {"type": "plain_text_input", "action_id": "ticket_input"}, "label": {"type": "plain_text", "text": "Ticket"}},
                {"type": "input", "block_id": "entitlement", "element": {"type": "static_select", "action_id": "entitlement_select", "placeholder": {"type": "plain_text", "text": "Select an entitlement"}, "options": [{"text": {"type": "plain_text", "text": option}, "value": option} for option in ["Enterprise Signature", "Enterprise Premier", "Enterprise Standard", "Online Customer"]]}, "label": {"type": "plain_text", "text": "Entitlement"}},
                # Add more fields here as per your requirement
                {"type": "actions", "block_id": "form_actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Submit"}, "style": "primary", "action_id": "submit_swarm_request"}]}
            ]
        }
    )

# Handle form submission from the modal
@app.action("submit_swarm_request")
def handle_submit_swarm_request(ack, body, client):
    # Acknowledge the action
    ack()
    
    user_id = body["user"]["id"]
    response_url = body["response_url"]

    # Handle the form submission and process the data
    client.chat_postMessage(channel="#general", text=f"<@{user_id}> submitted a swarm request.")

if __name__ == "__main__":
    # Initialize the Socket Mode handler to listen for events
    #handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    app.start(port=int(os.environ.get("PORT", 3000)))
