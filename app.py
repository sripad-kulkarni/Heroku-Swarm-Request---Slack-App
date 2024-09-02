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

# Handle the "Resolve Swarm" button click
@app.action("resolve_button")
def handle_resolve_button(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]  # Use message_ts as ID

    try:
        # Remove the pin from the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
        
        # Update the message to reflect it as resolved
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
        
        # Update the database
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE swarm_requests
                SET status = 'resolved'
                WHERE ticket = %s
                """,
                (body["message"]["text"],)  # Adjust the query based on your schema
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Error updating database: {e}")
        finally:
            cur.close()
            conn.close()
    except SlackApiError as e:
        logging.error(f"Error handling resolve button: {e.response['error']}")

# Handle the "Discard Swarm" button click
@app.action("discard_button")
def handle_discard_button(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]  # Use message_ts as ID

    try:
        # Remove the pin from the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
        
        # Update the message to reflect it as discarded
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
        
        # Update the database
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE swarm_requests
                SET status = 'discarded'
                WHERE ticket = %s
                """,
                (body["message"]["text"],)  # Adjust the query based on your schema
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Error updating database: {e}")
        finally:
            cur.close()
            conn.close()
    except SlackApiError as e:
        logging.error(f"Error handling discard button: {e.response['error']}")

# Handle the "Re-Open Swarm" button click
@app.action("reopen_button")
def handle_reopen_button(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]  # Use message_ts as ID

    try:
        # Update the message to reflect it as reopened
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text="This swarm request has been reopened.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This swarm request has been reopened and needs attention."
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
            ]
        )
        
        # Add a pin to the message
        client.pins_add(channel=channel_id, timestamp=message_ts)
        
        # Update the database
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE swarm_requests
                SET status = 'open'
                WHERE ticket = %s
                """,
                (body["message"]["text"],)  # Adjust the query based on your schema
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Error updating database: {e}")
        finally:
            cur.close()
            conn.close()
    except SlackApiError as e:
        logging.error(f"Error handling reopen button: {e.response['error']}")

# Update App Home tab
@app.event("app_home_opened")
def update_home_tab(client, event):
    try:
        view = get_home_tab_view()
        client.views_publish(
            user_id=event["user"],
            view=view
        )
    except SlackApiError as e:
        logging.error(f"Error publishing home tab view: {e.response['error']}")

def get_home_tab_view():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Fetch total statistics
        cur.execute("SELECT COUNT(*) FROM swarm_requests")
        total_requests = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'resolved'")
        total_resolved = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'discarded'")
        total_discarded = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM swarm_requests WHERE status = 'open'")
        total_open = cur.fetchone()[0]

        # Fetch user statistics
        cur.execute("""
            SELECT user_id, 
                   COUNT(*) AS requests_created
            FROM swarm_requests
            GROUP BY user_id
        """)
        user_stats = cur.fetchall()

        user_stats_blocks = []
        for user_id, requests_created in user_stats:
            # Replace user_id with display name if needed
            display_name = user_id  # Adjust if you have a way to fetch display names
            user_stats_blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{display_name}:*\nCreated {requests_created} requests, Posted X comments"
                    }
                }
            )
        
    except Exception as e:
        logging.error(f"Error fetching stats from database: {e}")
        total_requests, total_resolved, total_discarded, total_open = 0, 0, 0, 0
        user_stats_blocks = []

    finally:
        cur.close()
        conn.close()

    return {
        "type": "home",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Swarm Requests:*\n{total_requests}\n"
                            f"*Total Open Requests:*\n{total_open}\n"
                            f"*Total Resolved Requests:*\n{total_resolved}\n"
                            f"*Total Discarded Requests:*\n{total_discarded}\n"
                }
            },
            *user_stats_blocks  # Add user statistics blocks
        ]
    }

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
