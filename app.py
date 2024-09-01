from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime, timedelta
import schedule
import threading
import time

# Initialize the Slack Bolt app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Connect to PostgreSQL using DATABASE_URL
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    parsed_url = urlparse(database_url)
    conn = psycopg2.connect(
        dbname=parsed_url.path[1:],  # remove the leading '/'
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port
    )
    return conn

# Handle the slash command
@app.command("/swarmrequest")
def handle_swarm_request(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    user_id = body["user_id"]

    client.views_open(
        trigger_id=trigger_id,
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
                    "label": {"type": "plain_text", "text": "Ticket"},
                    "element": {"type": "plain_text_input", "action_id": "ticket_input"}
                },
                {
                    "type": "input",
                    "block_id": "entitlement",
                    "label": {"type": "plain_text", "text": "Entitlement"},
                    "element": {
                        "type": "static_select",
                        "action_id": "entitlement_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": "Enterprise Signature"}, "value": "enterprise_signature"},
                            {"text": {"type": "plain_text", "text": "Enterprise Premier"}, "value": "enterprise_premier"},
                            {"text": {"type": "plain_text", "text": "Enterprise Standard"}, "value": "enterprise_standard"},
                            {"text": {"type": "plain_text", "text": "Online Customer"}, "value": "online_customer"}
                        ]
                    }
                },
                {
                    "type": "input",
                    "block_id": "skill_group",
                    "label": {"type": "plain_text", "text": "Skill Group"},
                    "element": {
                        "type": "static_select",
                        "action_id": "skill_group_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": "Data"}, "value": "data"},
                            {"text": {"type": "plain_text", "text": "Runtime"}, "value": "runtime"},
                            {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "platform_web_services"},
                            {"text": {"type": "plain_text", "text": "Account Management"}, "value": "account_management"},
                            {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                        ]
                    }
                },
                {
                    "type": "input",
                    "block_id": "support_tier",
                    "label": {"type": "plain_text", "text": "Support Tier"},
                    "element": {
                        "type": "static_select",
                        "action_id": "support_tier_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": "High Complexity"}, "value": "high_complexity"},
                            {"text": {"type": "plain_text", "text": "General Usage"}, "value": "general_usage"}
                        ]
                    }
                },
                {
                    "type": "input",
                    "block_id": "priority",
                    "label": {"type": "plain_text", "text": "Priority"},
                    "element": {
                        "type": "static_select",
                        "action_id": "priority_select",
                        "options": [
                            {"text": {"type": "plain_text", "text": "Critical"}, "value": "critical"},
                            {"text": {"type": "plain_text", "text": "Urgent"}, "value": "urgent"},
                            {"text": {"type": "plain_text", "text": "High"}, "value": "high"},
                            {"text": {"type": "plain_text", "text": "Normal"}, "value": "normal"},
                            {"text": {"type": "plain_text", "text": "Low"}, "value": "low"}
                        ]
                    }
                },
                {
                    "type": "input",
                    "block_id": "issue_description",
                    "label": {"type": "plain_text", "text": "Issue Description"},
                    "element": {"type": "plain_text_input", "multiline": True, "action_id": "issue_description_input"}
                },
                {
                    "type": "input",
                    "block_id": "help_required",
                    "label": {"type": "plain_text", "text": "Help Required"},
                    "element": {"type": "plain_text_input", "multiline": True, "action_id": "help_required_input"}
                }
            ]
        }
    )

# Handle modal submissions
@app.view("swarm_request_form")
def handle_modal_submission(ack, body, client):
    ack()
    values = body["view"]["state"]["values"]
    ticket = values["ticket"]["ticket_input"]["value"]
    entitlement = values["entitlement"]["entitlement_select"]["selected_option"]["value"]
    skill_group = values["skill_group"]["skill_group_select"]["selected_option"]["value"]
    support_tier = values["support_tier"]["support_tier_select"]["selected_option"]["value"]
    priority = values["priority"]["priority_select"]["selected_option"]["value"]
    issue_description = values["issue_description"]["issue_description_input"]["value"]
    help_required = values["help_required"]["help_required_input"]["value"]
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]

    # Insert the request into the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"),
        [ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id, datetime.utcnow()]
    )
    swarm_request_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    # Post the form data to the same channel
    client.chat_postMessage(
        channel=channel_id,
        text=f"Swarm Request:\n"
             f"Ticket: {ticket}\n"
             f"Entitlement: {entitlement}\n"
             f"Skill Group: {skill_group}\n"
             f"Support Tier: {support_tier}\n"
             f"Priority: {priority}\n"
             f"Issue Description: {issue_description}\n"
             f"Help Required: {help_required}\n",
        blocks=[
            {
                "type": "section",
                "block_id": "request_summary",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Request*\n"
                            f"*Ticket:* {ticket}\n"
                            f"*Entitlement:* {entitlement}\n"
                            f"*Skill Group:* {skill_group}\n"
                            f"*Support Tier:* {support_tier}\n"
                            f"*Priority:* {priority}\n"
                            f"*Issue Description:* {issue_description}\n"
                            f"*Help Required:* {help_required}"
                }
            },
            {
                "type": "actions",
                "block_id": "request_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Resolve Swarm"},
                        "action_id": "resolve_swarm",
                        "style": "primary",
                        "value": f"resolve_{swarm_request_id}"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Discard Swarm"},
                        "action_id": "discard_swarm",
                        "style": "danger",
                        "value": f"discard_{swarm_request_id}"
                    }
                ]
            }
        ]
    )

    # Set up a reminder
    reminder_text = f"Reminder: Swarm request with ID {swarm_request_id} has been created."
    client.chat_postMessage(
        channel=channel_id,
        text=reminder_text
    )

@app.action("resolve_swarm")
def handle_resolve_swarm(ack, body, client):
    ack()
    swarm_request_id = body["actions"][0]["value"].split("_")[1]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    # Update the message
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="Swarm Request Resolved",
        blocks=[
            {
                "type": "section",
                "block_id": "resolved",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been resolved."
                }
            },
            {
                "type": "actions",
                "block_id": "reopen_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "action_id": "reopen_swarm",
                        "value": f"reopen_{swarm_request_id}"
                    }
                ]
            }
        ]
    )

    # Update the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s, resolved_at = %s WHERE id = %s"),
        ["resolved", datetime.utcnow(), swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

@app.action("discard_swarm")
def handle_discard_swarm(ack, body, client):
    ack()
    swarm_request_id = body["actions"][0]["value"].split("_")[1]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    # Update the message
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="Swarm Request Discarded",
        blocks=[
            {
                "type": "section",
                "block_id": "discarded",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been discarded."
                }
            },
            {
                "type": "actions",
                "block_id": "reopen_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "action_id": "reopen_swarm",
                        "value": f"reopen_{swarm_request_id}"
                    }
                ]
            }
        ]
    )

    # Update the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s, discarded_at = %s WHERE id = %s"),
        ["discarded", datetime.utcnow(), swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

@app.action("reopen_swarm")
def handle_reopen_swarm(ack, body, client):
    ack()
    swarm_request_id = body["actions"][0]["value"].split("_")[1]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    # Update the message
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="Swarm Request Reopened",
        blocks=[
            {
                "type": "section",
                "block_id": "reopened",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been reopened."
                }
            }
        ]
    )

    # Update the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s WHERE id = %s"),
        ["open", swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

# Schedule a reminder for unresolved requests
def check_unresolved_requests():
    now = datetime.utcnow()
    reminder_time = now - timedelta(hours=24)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("SELECT id, user_id, channel_id FROM swarm_requests WHERE status = %s AND created_at < %s"),
        ["open", reminder_time]
    )
    rows = cursor.fetchall()

    for row in rows:
        swarm_request_id, user_id, channel_id = row
        client.chat_postMessage(
            channel=channel_id,
            text=f"Reminder: Swarm request with ID {swarm_request_id} is unresolved.",
            blocks=[
                {
                    "type": "section",
                    "block_id": "reminder",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Reminder: Swarm request with ID {swarm_request_id} is unresolved and needs attention."
                    }
                },
                {
                    "type": "actions",
                    "block_id": "reminder_actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Still Need Help?"},
                            "action_id": "still_need_help",
                            "value": f"help_{swarm_request_id}"
                        }
                    ]
                }
            ]
        )

    cursor.close()
    conn.close()

def schedule_jobs():
    schedule.every().hour.do(check_unresolved_requests)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Start the scheduler in a separate thread
    threading.Thread(target=schedule_jobs).start()

    # Start the Slack Bolt app with SocketModeHandler
    app.start(port=int(os.environ.get("PORT", 3000)))
