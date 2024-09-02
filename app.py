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
    message_ts = body["message"]["ts"]

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

# Handle the "Discard Swarm" button click
@app.action("discard_button")
def handle_discard_button(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

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

# Handle the "Re-Open Swarm" button click
@app.action("reopen_button")
def handle_reopen_swarm(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

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

        client.pins_add(channel=channel_id, timestamp=message_ts)


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

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
