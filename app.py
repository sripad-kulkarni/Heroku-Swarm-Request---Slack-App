from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import psycopg2
from psycopg2 import sql
import schedule
import time
import threading
from datetime import datetime, timedelta

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
                # Blocks for form fields...
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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id, message_ts) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"),
        [ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id, None]
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

# Handle interactive button clicks
@app.action("resolve_swarm")
def handle_resolve_swarm(ack, body, client):
    ack()
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    user_id = body["user"]["id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s WHERE channel_id = %s AND message_ts = %s"),
        ['resolved', channel_id, message_ts]
    )
    conn.commit()
    cursor.close()
    conn.close()

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="The swarm request has been resolved. Thank you!",
        blocks=[
            {
                "type": "section",
                "block_id": "summary",
                "text": {
                    "type": "mrkdwn",
                    "text": "The swarm request has been resolved."
                }
            },
            {
                "type": "actions",
                "block_id": "action_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "action_id": "reopen_swarm",
                        "style": "primary"
                    }
                ]
            }
        ]
    )

@app.action("discard_swarm")
def handle_discard_swarm(ack, body, client):
    ack()
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    user_id = body["user"]["id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s WHERE channel_id = %s AND message_ts = %s"),
        ['discarded', channel_id, message_ts]
    )
    conn.commit()
    cursor.close()
    conn.close()

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="The swarm request has been discarded.",
        blocks=[
            {
                "type": "section",
                "block_id": "summary",
                "text": {
                    "type": "mrkdwn",
                    "text": "The swarm request has been discarded."
                }
            },
            {
                "type": "actions",
                "block_id": "action_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "action_id": "reopen_swarm",
                        "style": "primary"
                    }
                ]
            }
        ]
    )

@app.action("reopen_swarm")
def handle_reopen_swarm(ack, body, client):
    ack()
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    user_id = body["user"]["id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        sql.SQL("UPDATE swarm_requests SET status = %s WHERE channel_id = %s AND message_ts = %s"),
        ['open',
