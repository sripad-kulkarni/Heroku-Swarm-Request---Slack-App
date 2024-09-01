import os
import json
import psycopg2
import schedule
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize the app with your bot token and app token
app = App(token=os.environ["SLACK_BOT_TOKEN"])
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Connect to your PostgreSQL database
def get_db_connection():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    return conn

# Command to open the modal
@app.command("/swarmrequest")
def handle_swarm_request(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]

    # Define the modal view
    modal_view = {
        "type": "modal",
        "callback_id": "swarm_request_form",
        "title": {"type": "plain_text", "text": "Swarm Request"},
        "blocks": [
            {"type": "input", "block_id": "ticket", "label": {"type": "plain_text", "text": "Ticket"}, "element": {"type": "plain_text_input", "action_id": "ticket"}},
            {"type": "input", "block_id": "entitlement", "label": {"type": "plain_text", "text": "Entitlement"}, "element": {"type": "static_select", "action_id": "entitlement", "options": [{"text": {"type": "plain_text", "text": "Enterprise Signature"}, "value": "enterprise_signature"}, {"text": {"type": "plain_text", "text": "Enterprise Premier"}, "value": "enterprise_premier"}, {"text": {"type": "plain_text", "text": "Enterprise Standard"}, "value": "enterprise_standard"}, {"text": {"type": "plain_text", "text": "Online Customer"}, "value": "online_customer"}]}},
            {"type": "input", "block_id": "skill_group", "label": {"type": "plain_text", "text": "Skill Group"}, "element": {"type": "static_select", "action_id": "skill_group", "options": [{"text": {"type": "plain_text", "text": "Data"}, "value": "data"}, {"text": {"type": "plain_text", "text": "Runtime"}, "value": "runtime"}, {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "platform_web_services"}, {"text": {"type": "plain_text", "text": "Account Management"}, "value": "account_management"}, {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}]}},
            {"type": "input", "block_id": "support_tier", "label": {"type": "plain_text", "text": "Support Tier"}, "element": {"type": "static_select", "action_id": "support_tier", "options": [{"text": {"type": "plain_text", "text": "High Complexity"}, "value": "high_complexity"}, {"text": {"type": "plain_text", "text": "General Usage"}, "value": "general_usage"}]}},
            {"type": "input", "block_id": "priority", "label": {"type": "plain_text", "text": "Priority"}, "element": {"type": "static_select", "action_id": "priority", "options": [{"text": {"type": "plain_text", "text": "Critical"}, "value": "critical"}, {"text": {"type": "plain_text", "text": "Urgent"}, "value": "urgent"}, {"text": {"type": "plain_text", "text": "High"}, "value": "high"}, {"text": {"type": "plain_text", "text": "Normal"}, "value": "normal"}, {"text": {"type": "plain_text", "text": "Low"}, "value": "low"}]}},
            {"type": "input", "block_id": "issue_description", "label": {"type": "plain_text", "text": "Issue Description"}, "element": {"type": "plain_text_input", "action_id": "issue_description", "multiline": True}},
            {"type": "input", "block_id": "help_required", "label": {"type": "plain_text", "text": "Help Required"}, "element": {"type": "plain_text_input", "action_id": "help_required", "multiline": True}},
            {"type": "actions", "block_id": "submit_block", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Submit"}, "action_id": "submit_button"}]}
        ]
    }

    try:
        client.views_open(trigger_id=trigger_id, view=modal_view)
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")

# Handle modal submission
@app.view("swarm_request_form")
def handle_modal_submission(ack, body, client):
    ack()
    view = body["view"]
    user_id = body["user"]["id"]
    values = view["state"]["values"]

    # Extract values from the form
    ticket = values["ticket"]["ticket"]["value"]
    entitlement = values["entitlement"]["entitlement"]["selected_option"]["value"]
    skill_group = values["skill_group"]["skill_group"]["selected_option"]["value"]
    support_tier = values["support_tier"]["support_tier"]["selected_option"]["value"]
    priority = values["priority"]["priority"]["selected_option"]["value"]
    issue_description = values["issue_description"]["issue_description"]["value"]
    help_required = values["help_required"]["help_required"]["value"]

    # Post the message in the channel
    try:
        result = client.chat_postMessage(
            channel="general",  # Replace with your channel ID
            text=f"New Swarm Request:\n*Ticket:* {ticket}\n*Entitlement:* {entitlement}\n*Skill Group:* {skill_group}\n*Support Tier:* {support_tier}\n*Priority:* {priority}\n*Issue Description:* {issue_description}\n*Help Required:* {help_required}",
            attachments=[
                {
                    "text": "Action required",
                    "fallback": "Resolve or discard this swarm request.",
                    "actions": [
                        {
                            "name": "resolve",
                            "text": "Resolve Swarm",
                            "type": "button",
                            "value": "resolve",
                            "style": "primary"
                        },
                        {
                            "name": "discard",
                            "text": "Discard Swarm",
                            "type": "button",
                            "value": "discard",
                            "style": "danger"
                        }
                    ]
                }
            ]
        )
        message_ts = result["ts"]
        channel_id = result["channel"]

        # Save request to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO swarm_requests (user_id, ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, channel_id, message_ts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, channel_id, message_ts)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Pin the message
        client.pins_add(channel=channel_id, timestamp=message_ts)
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

# Handle button interactions
@app.action("resolve_swarm")
def handle_resolve_swarm(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    message_ts = body["message_ts"]
    
    # Update the message
    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Swarm request resolved.",
            attachments=[{
                "text": "Re-open Swarm",
                "fallback": "Re-open this swarm request.",
                "actions": [
                    {
                        "name": "reopen",
                        "text": "Re-Open Swarm",
                        "type": "button",
                        "value": "reopen"
                    }
                ]
            }]
        )
        # Unpin the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
    except SlackApiError as e:
        print(f"Error updating message: {e.response['error']}")

@app.action("discard_swarm")
def handle_discard_swarm(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    message_ts = body["message_ts"]

    # Update the message
    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Swarm request discarded.",
            attachments=[{
                "text": "Re-open Swarm",
                "fallback": "Re-open this swarm request.",
                "actions": [
                    {
                        "name": "reopen",
                        "text": "Re-Open Swarm",
                        "type": "button",
                        "value": "reopen"
                    }
                ]
            }]
        )
        # Unpin the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
    except SlackApiError as e:
        print(f"Error updating message: {e.response['error']}")

@app.action("reopen_swarm")
def handle_reopen_swarm(ack, body, client):
    ack()
    channel_id = body["channel"]["id"]
    message_ts = body["message_ts"]

    # Update the message to reflect that it's reopened
    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="Swarm request reopened.",
            attachments=[{
                "text": "Resolve or Discard Swarm",
                "fallback": "Resolve or discard this swarm request.",
                "actions": [
                    {
                        "name": "resolve",
                        "text": "Resolve Swarm",
                        "type": "button",
                        "value": "resolve",
                        "style": "primary"
                    },
                    {
                        "name": "discard",
                        "text": "Discard Swarm",
                        "type": "button",
                        "value": "discard",
                        "style": "danger"
                    }
                ]
            }]
        )
    except SlackApiError as e:
        print(f"Error updating message: {e.response['error']}")

# Schedule reminders
def send_reminders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, channel_id, message_ts FROM swarm_requests WHERE updated_at < NOW() - INTERVAL '24 hours'")
    rows = cursor.fetchall()
    for row in rows:
        user_id, channel_id, message_ts = row
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Reminder: Your swarm request at {message_ts} is unresolved. Please take action.",
                attachments=[{
                    "text": "Still Need Help?",
                    "fallback": "Still need help?",
                    "actions": [
                        {
                            "name": "still_need_help",
                            "text": "Still Need Help?",
                            "type": "button",
                            "value": "still_need_help"
                        }
                    ]
                }]
            )
        except SlackApiError as e:
            print(f"Error sending reminder: {e.response['error']}")
    cursor.close()
    conn.close()

# Set up a schedule to send reminders every hour
schedule.every().hour.do(send_reminders)

# Update the app home with statistics
@app.event("app_home_opened")
def handle_app_home_opened(client, event):
    user_id = event["user"]
    # Generate statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM swarm_requests WHERE user_id = %s
    """, (user_id,))
    user_swarm_count = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM swarm_requests
    """)
    total_swarm_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    # Update the app home with statistics
    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "block_id": "stats_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Your Swarm Requests:* {user_swarm_count}\n*Total Swarm Requests:* {total_swarm_count}"
                        }
                    }
                ]
            }
        )
    except SlackApiError as e:
        print(f"Error updating app home: {e.response['error']}")

# Start the app
if __name__ == "__main__":
    handler = SocketModeHandler(app, app_token=os.environ["SLACK_APP_TOKEN"])
    handler.start()