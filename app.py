from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
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
    user_id = body["user_id"]
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
        sql.SQL("INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"),
        [ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id]
    )
    swarm_request_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    # Post the form data to the same channel
    result = client.chat_postMessage(
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
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Discard Swarm"},
                        "action_id": "discard_swarm",
                        "style": "danger"
                    }
                ]
            }
        ]
    )

    # Update the database with the message timestamp
    message_ts = result["ts"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET message_ts = %s WHERE id = %s"),
        [message_ts, swarm_request_id]
    )
    conn.commit()
    cursor.close()
    conn.close()

# Handle interactive
