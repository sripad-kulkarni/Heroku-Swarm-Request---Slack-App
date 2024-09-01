import os
import logging
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import psycopg2
from psycopg2 import sql
import schedule
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

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

# Function to handle modal submission
@app.view("swarm_request_form")
def handle_modal_submission(ack, body, view, client):
    ack()

    # Extract data from the form submission
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]  # Channel ID is obtained from the body
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

# Handle reminders
def check_pending_requests():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, channel_id, created_at
            FROM swarm_requests
            WHERE status = 'Pending' AND created_at < %s;
        """, (datetime.now() - timedelta(days=1),))
        requests = cursor.fetchall()

    for request in requests:
        request_id, user_id, channel_id, created_at = request
        message = f"Reminder: Swarm request <@{user_id}> from {created_at} is still pending."
        app.client.chat_postMessage(
            channel=channel_id,
            text=message,
            attachments=[
                {
                    "text": "Still need help?",
                    "fallback": "You are unable to choose an action",
                    "callback_id": f"reminder_{request_id}",
                    "actions": [
                        {
                            "name": "still_need_help",
                            "text": "Still Need Help?",
                            "type": "button",
                            "value": "still_need_help"
                        }
                    ]
                }
            ]
        )

# Schedule reminders
scheduler = BackgroundScheduler()
scheduler.add_job(check_pending_requests, 'interval', hours=24)
scheduler.start()

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
