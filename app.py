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
                # Modal blocks here...
            ],
            # Add a hidden input field to store the original channel ID
            "private_metadata": body["channel_id"]
        }
    )

@app.view("swarm_request_form")
def handle_modal_submission(ack, body, view, client):
    ack()

    # Extract values from the modal submission
    # Extract values from the modal submission...
    
    # Get the channel ID from the context
    channel_id = body["view"]["private_metadata"]
    user_id = body["user"]["id"]
    
    # Post message to the channel with buttons
    try:
        result = client.chat_postMessage(
            channel=channel_id,
            blocks=[
                # Message blocks here...
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
    message_ts = body["message"]["ts"]  # Use message timestamp as ID

    try:
        # Remove the pin from the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
        
        # Update the original message to reflect the resolved status
        updated_blocks = [
            block for block in body["message"]["blocks"] if block["type"] != "actions"
        ] + [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Swarm request resolved by <@{user_id}>."}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "style": "primary",
                        "value": "reopen",
                        "action_id": "reopen_button"
                    }
                ]
            }
        ]
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks
        )

        # Update or insert the row in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO swarm_requests (id, status)
            VALUES (%s, 'resolved')
            ON CONFLICT (id) DO UPDATE
            SET status = 'resolved', updated_at = CURRENT_TIMESTAMP
            """,
            (message_ts,)
        )
        conn.commit()
        cur.close()
        conn.close()
        
    except SlackApiError as e:
        logging.error(f"Error resolving swarm request: {e.response['error']}")

@app.action("discard_button")
def handle_discard_button(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]  # Use message timestamp as ID

    try:
        # Remove the pin from the message
        client.pins_remove(channel=channel_id, timestamp=message_ts)
        
        # Update the original message to reflect the discarded status
        updated_blocks = [
            block for block in body["message"]["blocks"] if block["type"] != "actions"
        ] + [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Swarm request discarded by <@{user_id}>."}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Re-Open Swarm"},
                        "style": "primary",
                        "value": "reopen",
                        "action_id": "reopen_button"
                    }
                ]
            }
        ]
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks
        )

        # Update or insert the row in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO swarm_requests (id, status)
            VALUES (%s, 'discarded')
            ON CONFLICT (id) DO UPDATE
            SET status = 'discarded', updated_at = CURRENT_TIMESTAMP
            """,
            (message_ts,)
        )
        conn.commit()
        cur.close()
        conn.close()
        
    except SlackApiError as e:
        logging.error(f"Error discarding swarm request: {e.response['error']}")

@app.action("reopen_button")
def handle_reopen_swarm(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]  # Use message timestamp as ID

    try:
        # Post a new message in the thread indicating the swarm request has been reopened
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=message_ts,
            text="The swarm request has been reopened and needs attention."
        )

        # Update the original message to show the previous two buttons
        updated_blocks = [
            block for block in body["message"]["blocks"]
            if not (
                (block.get("type") == "section" and
                 "Swarm request resolved by" in block.get("text", {}).get("text", "")) or
                (block.get("type") == "actions" and
                 any(button.get("text", {}).get("text", "") == "Re-Open Swarm" for button in block.get("elements", [])))
            )
        ]
        
        updated_blocks.append(
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Resolve Swarm"}, "style": "primary", "action_id": "resolve_button"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Discard Swarm"}, "style": "danger", "action_id": "discard_button"}
                ]
            }
        )

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=updated_blocks
        )

        # Update or insert the row in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO swarm_requests (id, status)
            VALUES (%s, 'reopened')
            ON CONFLICT (id) DO UPDATE
            SET status = 'reopened', updated_at = CURRENT_TIMESTAMP
            """,
            (message_ts,)
        )
        conn.commit()
        cur.close()
        conn.close()
        
    except SlackApiError as e:
        logging.error(f"Error reopening swarm request: {e.response['error']}")

# Run the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
