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
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                            "style": "danger",
                            "value": "reopen",
                            "action_id": "reopen_button"
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
            INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, result["ts"], "open")
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error storing data in database: {e}")
    finally:
        cur.close()
        conn.close()

# Handle the "Resolve Swarm" button click
@app.action("resolve_button")
def handle_resolve_swarm(ack, body, client):
    ack()

    # Extract necessary information from the action
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    # Update the database to mark the request as resolved
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE swarm_requests SET status = %s WHERE id = %s
            """,
            ("resolved", message_ts)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating database: {e}")
    finally:
        cur.close()
        conn.close()

    # Update the message in the channel
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="This swarm request has been resolved.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been resolved."
                }
            }
        ]
    )

# Handle the "Discard Swarm" button click
@app.action("discard_button")
def handle_discard_swarm(ack, body, client):
    ack()

    # Extract necessary information from the action
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    # Update the database to mark the request as discarded
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE swarm_requests SET status = %s WHERE id = %s
            """,
            ("discarded", message_ts)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating database: {e}")
    finally:
        cur.close()
        conn.close()

    # Update the message in the channel
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="This swarm request has been discarded.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been discarded."
                }
            }
        ]
    )

# Handle the "Re-Open Swarm" button click
@app.action("reopen_button")
def handle_reopen_swarm(ack, body, client):
    ack()

    # Extract necessary information from the action
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    # Update the database to mark the request as reopened
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE swarm_requests SET status = %s WHERE id = %s
            """,
            ("open", message_ts)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error updating database: {e}")
    finally:
        cur.close()
        conn.close()

    # Post a new message in the thread indicating the swarm request is reopened
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=message_ts,
        text="The swarm request has been reopened and needs attention."
    )

    # Update the original message
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="This swarm request has been reopened and needs attention.",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This swarm request has been reopened and needs attention."
                }
            }
        ]
    )

# Handler for app home
@app.event("app_home_opened")
def handle_app_home_opened(event, client):
    user_id = event["user"]

    # Fetch user info
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["real_name"]

    # Fetch statistics from the database
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'open'")
        open_requests = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'resolved'")
        resolved_requests = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'discarded'")
        discarded_requests = cur.fetchone()[0]
        total_requests = open_requests + resolved_requests + discarded_requests
    except Exception as e:
        logging.error(f"Error fetching statistics from database: {e}")
        open_requests = resolved_requests = discarded_requests = total_requests = 0
    finally:
        cur.close()
        conn.close()

    # Post the app home view
    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "block_id": "welcome",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Welcome, {user_name}!"
                    }
                },
                {
                    "type": "section",
                    "block_id": "stats",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Total Swarm Requests:* {total_requests}\n"
                                f"*Total Open Requests:* {open_requests}\n"
                                f"*Total Resolved Requests:* {resolved_requests}\n"
                                f"*Total Discarded Requests:* {discarded_requests}"
                    }
                }
            ]
        }
    )

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
