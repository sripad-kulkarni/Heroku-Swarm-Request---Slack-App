import os
import logging
import psycopg2
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Set up logging
logging.basicConfig(level=logging.INFO)

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return conn
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        raise

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
            ],
            # Add a hidden input field to store the original channel ID
            "private_metadata": body["channel_id"]
        }
    )

@app.view("swarm_request_form")
def handle_modal_submission(ack, body, view, client):
    ack()

    # Extract values from the modal submission
    ticket = view["state"]["values"]["ticket"]["ticket_input"]["value"]
    entitlement = view["state"]["values"]["entitlement"]["entitlement_select"]["selected_option"]["value"]
    skill_group = view["state"]["values"]["skill_group"]["skill_group_select"]["selected_option"]["value"]
    support_tier = view["state"]["values"]["support_tier"]["support_tier_select"]["selected_option"]["value"]
    priority = view["state"]["values"]["priority"]["priority_select"]["selected_option"]["value"]
    issue_description = view["state"]["values"]["issue_description"]["issue_description_input"]["value"]
    help_required = view["state"]["values"]["help_required"]["help_required_input"]["value"]
    
    # Get the channel ID from the context
    channel_id = body["view"]["private_metadata"]
    user_id = body["user"]["id"]
    
    # Post message to the channel with buttons
    try:
        result = client.chat_postMessage(
            channel=channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*New Swarm Request*\n"
                                f"Ticket: {ticket}\n"
                                f"Entitlement: {entitlement}\n"
                                f"Skill Group: {skill_group}\n"
                                f"Support Tier: {support_tier}\n"
                                f"Priority: {priority}\n"
                                f"Issue Description: {issue_description}\n"
                                f"Help Required: {help_required}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Resolve Swarm"},
                            "style": "primary",
                            "value": "resolve",
                            "action_id": "resolve_button"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Discard Swarm"},
                            "style": "danger",
                            "value": "discard",
                            "action_id": "discard_button"
                        }
                    ]
                }
            ],
            text="New Swarm Request",
            user=user_id,
            unfurl_links=True
        )
        # Pin the message to the channel
        client.pins_add(channel=channel_id, timestamp=result["ts"])
    except SlackApiError as e:
        logging.error(f"Error posting message: {e.response['error']}")
    
    # Store the form data in the database
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error storing data in database: {e}")
    finally:
        cur.close()
        conn.close()


@app.action("resolve_swarm")
def handle_resolve_swarm(ack, body, client):
    ack()
    # Get message details
    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]
    
    # Update the original message to indicate it has been resolved
    client.chat_update(
        channel=channel_id,
        ts=ts,
        text=f"{body['message']['text']}\n\n*Status: Resolved*",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"{body['message']['text']}\n\n*Status: Resolved*"}},
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Re-Open Swarm"}, "style": "primary", "action_id": "reopen_swarm"}
                ]
            }
        ]
    )

    # Unpin the message
    client.pins_remove(channel=channel_id, timestamp=ts)

@app.action("discard_swarm")
def handle_discard_swarm(ack, body, client):
    ack()
    # Get message details
    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]
    
    # Update the original message to indicate it has been discarded
    client.chat_update(
        channel=channel_id,
        ts=ts,
        text=f"{body['message']['text']}\n\n*Status: Discarded*",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"{body['message']['text']}\n\n*Status: Discarded*"}},
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Re-Open Swarm"}, "style": "primary", "action_id": "reopen_swarm"}
                ]
            }
        ]
    )

    # Unpin the message
    client.pins_remove(channel=channel_id, timestamp=ts)

@app.action("reopen_swarm")
def handle_reopen_swarm(ack, body, client):
    ack()
    # Get message details
    channel_id = body["channel"]["id"]
    ts = body["message"]["ts"]
    
    # Post a new message in the thread indicating the swarm request has been reopened
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=ts,
        text="The swarm request has been reopened and needs attention."
    )

    # Update the original message to show the previous two buttons
    client.chat_update(
        channel=channel_id,
        ts=ts,
        text=f"{body['message']['text']}\n\n*Status: Reopened - Needs Attention*",
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"{body['message']['text']}\n\n*Status: Reopened - Needs Attention*"}},
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Resolve Swarm"}, "style": "primary", "action_id": "resolve_swarm"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Discard Swarm"}, "style": "danger", "action_id": "discard_swarm"}
                ]
            }
        ]
    )

# Function to remind user after 24 hours
def remind_user_after_24_hours(client, channel_id, user_id, message_ts):
    try:
        # Check if no action was taken on the swarm request
        response = client.conversations_history(channel=channel_id, latest=message_ts, inclusive=True, limit=1)
        if response["messages"][0]["text"].endswith("Swarm request unresolved."):
            client.chat_postMessage(
                channel=channel_id,
                text=f"<@{user_id}> Reminder: The swarm request is still unresolved. Do you still need help?",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"<@{user_id}> This swarm request needs action."}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Still Need Help?"},
                                "style": "primary",
                                "value": "still_need_help",
                                "action_id": "still_need_help_button"
                            }
                        ]
                    }
                ]
            )
    except SlackApiError as e:
        logging.error(f"Error sending reminder: {e.response['error']}")

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
