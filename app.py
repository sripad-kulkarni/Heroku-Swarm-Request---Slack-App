from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
import schedule
import threading
import time

# Initialize the Bolt app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Connect to PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT")
    )
    return conn

# Handle the slash command
@app.command("/swarmrequest")
def handle_swarm_request(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    channel_id = body["channel_id"]

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
                "block_id": "summary",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Request*\n"
                            f"*Ticket:* {ticket}\n"
                            f"*Entitlement:* {entitlement}\n"
                            f"*Skill Group:* {skill_group}\n"
                            f"*Support Tier:* {support_tier}\n"
                            f"*Priority:* {priority}\n"
                            f"*Issue Description:* {issue_description}\n"
                            f"*Help Required:* {help_required}\n"
                }
            },
            {
                "type": "actions",
                "block_id": "action_buttons",
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

# Handle button actions
@app.action("resolve_swarm")
def handle_resolve_swarm(ack, body, client):
    ack()
    swarm_request_id = body["actions"][0]["value"].split("_")[1]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    # Update the request in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET resolved_at = %s WHERE id = %s"),
        [datetime.utcnow(), swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Update the message in Slack
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"Swarm Request Resolved:\nRequest ID: {swarm_request_id}",
        blocks=[
            {
                "type": "section",
                "block_id": "resolved_summary",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Request Resolved*\n"
                            f"*Request ID:* {swarm_request_id}\n"
                            f"*Resolved At:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]
    )

@app.action("discard_swarm")
def handle_discard_swarm(ack, body, client):
    ack()
    swarm_request_id = body["actions"][0]["value"].split("_")[1]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    # Delete the request from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("DELETE FROM swarm_requests WHERE id = %s"),
        [swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Update the message in Slack
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text=f"Swarm Request Discarded:\nRequest ID: {swarm_request_id}",
        blocks=[
            {
                "type": "section",
                "block_id": "discarded_summary",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Swarm Request Discarded*\n"
                            f"*Request ID:* {swarm_request_id}\n"
                            f"*Discarded At:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]
    )

# Function to check and delete expired requests
def check_expired_requests():
    conn = get_db_connection()
    cursor = conn.cursor()
    expiration_time = datetime.utcnow() - timedelta(days=7)
    cursor.execute(
        sql.SQL("DELETE FROM swarm_requests WHERE created_at < %s AND resolved_at IS NULL"),
        [expiration_time]
    )
    conn.commit()
    cursor.close()
    conn.close()

# Schedule the task to run daily
def schedule_tasks():
    schedule.every().day.at("00:00").do(check_expired_requests)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the server
if __name__ == "__main__":
    # Start the scheduler thread
    scheduler_thread = threading.Thread(target=schedule_tasks)
    scheduler_thread.start()

    # Start the app
    if os.environ.get("SLACK_APP_TOKEN"):
        SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
    else:
        app.start(port=int(os.environ.get("PORT", 3000)))
