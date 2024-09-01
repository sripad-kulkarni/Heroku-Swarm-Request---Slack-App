import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import psycopg2

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Function to create tables if they don't exist
def create_tables():
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS swarm_requests (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                channel_id VARCHAR(255),
                ticket VARCHAR(255),
                entitlement VARCHAR(255),
                skill_group VARCHAR(255),
                support_tier VARCHAR(255),
                priority VARCHAR(255),
                issue_description TEXT,
                help_required TEXT,
                status VARCHAR(255) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                request_id INTEGER REFERENCES swarm_requests(id),
                user_id VARCHAR(255),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

create_tables()

# Handle the slash command
@app.command("/swarmrequest")
def handle_swarm_request(ack, body, client):
    # Acknowledge the command request immediately
    ack()

    # Open a modal with fields for the swarm request
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "swarm_request_form",
            "title": {"type": "plain_text", "text": "Create Swarm Request"},
            "submit": {"type": "plain_text", "text": "Submit"},
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
                {
                    "type": "input",
                    "block_id": "skill_group",
                    "element": {
                        "type": "static_select",
                        "action_id": "skill_group_select",
                        "placeholder": {"type": "plain_text", "text": "Select Skill Group"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Data"}, "value": "data"},
                            {"text": {"type": "plain_text", "text": "Runtime"}, "value": "runtime"},
                            {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "platform_web_services"},
                            {"text": {"type": "plain_text", "text": "Account Management"}, "value": "account_management"},
                            {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Skill Group"}
                },
                {
                    "type": "input",
                    "block_id": "support_tier",
                    "element": {
                        "type": "static_select",
                        "action_id": "support_tier_select",
                        "placeholder": {"type": "plain_text", "text": "Select Support Tier"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "High Complexity"}, "value": "high_complexity"},
                            {"text": {"type": "plain_text", "text": "General Usage"}, "value": "general_usage"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Support Tier"}
                },
                {
                    "type": "input",
                    "block_id": "priority",
                    "element": {
                        "type": "static_select",
                        "action_id": "priority_select",
                        "placeholder": {"type": "plain_text", "text": "Select Priority"},
                        "options": [
                            {"text": {"type": "plain_text", "text": "Critical"}, "value": "critical"},
                            {"text": {"type": "plain_text", "text": "Urgent"}, "value": "urgent"},
                            {"text": {"type": "plain_text", "text": "High"}, "value": "high"},
                            {"text": {"type": "plain_text", "text": "Normal"}, "value": "normal"},
                            {"text": {"type": "plain_text", "text": "Low"}, "value": "low"}
                        ]
                    },
                    "label": {"type": "plain_text", "text": "Priority"}
                },
                {
                    "type": "input",
                    "block_id": "issue_description",
                    "element": {"type": "plain_text_input", "multiline": True, "action_id": "issue_description_input"},
                    "label": {"type": "plain_text", "text": "Issue Description"}
                },
                {
                    "type": "input",
                    "block_id": "help_required",
                    "element": {"type": "plain_text_input", "multiline": True, "action_id": "help_required_input"},
                    "label": {"type": "plain_text", "text": "Help Required"}
                }
            ]
        }
    )

# Handle modal submission
@app.view("swarm_request_form")
def handle_modal_submission(ack, body, view, client):
    ack()

    # Extract data from the form submission
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    ticket = values["ticket"]["ticket_input"]["value"]
    entitlement = values["entitlement"]["entitlement_select"]["selected_option"]["value"]
    skill_group = values["skill_group"]["skill_group_select"]["selected_option"]["value"]
    support_tier = values["support_tier"]["support_tier_select"]["selected_option"]["value"]
    priority = values["priority"]["priority_select"]["selected_option"]["value"]
    issue_description = values["issue_description"]["issue_description_input"]["value"]
    help_required = values["help_required"]["help_required_input"]["value"]

    # Store the swarm request in the database
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO swarm_requests (user_id, channel_id, ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (user_id, channel_id, ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required))
        request_id = cursor.fetchone()[0]
        conn.commit()

    # Post the swarm request details to the channel
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=f"New Swarm Request submitted by <@{user_id}>:\n"
                 f"Ticket: {ticket}\n"
                 f"Entitlement: {entitlement}\n"
                 f"Skill Group: {skill_group}\n"
                 f"Support Tier: {support_tier}\n"
                 f"Priority: {priority}\n"
                 f"Issue Description: {issue_description}\n"
                 f"Help Required: {help_required}",
            attachments=[
                {
                    "text": "Actions:",
                    "fallback": "You are unable to choose an action",
                    "callback_id": f"swarm_request_{request_id}",
                    "actions": [
                        {
                            "name": "resolve",
                            "text": "Resolve Swarm",
                            "type": "button",
                            "style": "primary",
                            "value": "resolve"
                        },
                        {
                            "name": "discard",
                            "text": "Discard Swarm",
                            "type": "button",
                            "style": "danger",
                            "value": "discard"
                        }
                    ]
                }
            ]
        )
        # Pin the message to the channel
        client.pins_add(channel=channel_id, timestamp=response["ts"])
    except SlackApiError as e:
        logging.error(f"Error posting message: {e.response['error']}")

# Handle button interactions
@app.action("resolve")
def handle_resolve_action(ack, body, client):
    ack()
    request_id = body["callback_id"].split("_")[2]

    # Update the swarm request status
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE swarm_requests
            SET status = 'Resolved'
            WHERE id = %s;
        """, (request_id,))
        conn.commit()

    # Update the message
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Swarm Request Resolved",
        attachments=[
            {
                "text": "Actions:",
                "fallback": "You are unable to choose an action",
                "callback_id": f"swarm_request_{request_id}",
                "actions": [
                    {
                        "name": "reopen",
                        "text": "Re-Open Swarm",
                        "type": "button",
                        "value": "reopen"
                    }
                ]
            }
        ]
    )

@app.action("discard")
def handle_discard_action(ack, body, client):
    ack()
    request_id = body["callback_id"].split("_")[2]

    # Update the swarm request status
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE swarm_requests
            SET status = 'Discarded'
            WHERE id = %s;
        """, (request_id,))
        conn.commit()

    # Update the message
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Swarm Request Discarded",
        attachments=[
            {
                "text": "Actions:",
                "fallback": "You are unable to choose an action",
                "callback_id": f"swarm_request_{request_id}",
                "actions": [
                    {
                        "name": "reopen",
                        "text": "Re-Open Swarm",
                        "type": "button",
                        "value": "reopen"
                    }
                ]
            }
        ]
    )

@app.action("reopen")
def handle_reopen_action(ack, body, client):
    ack()
    request_id = body["callback_id"].split("_")[2]

    # Update the swarm request status
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE swarm_requests
            SET status = 'Pending'
            WHERE id = %s;
        """, (request_id,))
        conn.commit()

    # Update the message
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Swarm Request Re-Opened",
        attachments=[
            {
                "text": "Actions:",
                "fallback": "You are unable to choose an action",
                "callback_id": f"swarm_request_{request_id}",
                "actions": [
                    {
                        "name": "resolve",
                        "text": "Resolve Swarm",
                        "type": "button",
                        "style": "primary",
                        "value": "resolve"
                    },
                    {
                        "name": "discard",
                        "text": "Discard Swarm",
                        "type": "button",
                        "style": "danger",
                        "value": "discard"
                    }
                ]
            }
        ]
    )

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
