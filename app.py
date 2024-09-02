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
                            {"text": {"type": "plain_text", "text": "Enterprise Signature"}, "value": "Enterprise Signature"},
                            {"text": {"type": "plain_text", "text": "Enterprise Premier"}, "value": "Enterprise Premier"},
                            {"text": {"type": "plain_text", "text": "Enterprise Standard"}, "value": "Enterprise Standard"},
                            {"text": {"type": "plain_text", "text": "Online Customer"}, "value": "Online Customer"}
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
                            {"text": {"type": "plain_text", "text": "Data"}, "value": "Data"},
                            {"text": {"type": "plain_text", "text": "Runtime"}, "value": "Runtime"},
                            {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "Platform/Web Services"},
                            {"text": {"type": "plain_text", "text": "Account Management"}, "value": "Account Management"},
                            {"text": {"type": "plain_text", "text": "Other"}, "value": "Other"}
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
                            {"text": {"type": "plain_text", "text": "High Complexity"}, "value": "High Complexity"},
                            {"text": {"type": "plain_text", "text": "General Usage"}, "value": "General Usage"}
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
                            {"text": {"type": "plain_text", "text": "Critical"}, "value": "Critical"},
                            {"text": {"type": "plain_text", "text": "Urgent"}, "value": "Urgent"},
                            {"text": {"type": "plain_text", "text": "High"}, "value": "High"},
                            {"text": {"type": "plain_text", "text": "Normal"}, "value": "Normal"},
                            {"text": {"type": "plain_text", "text": "Low"}, "value": "Low"}
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


    # Fetch user info to display in the message
    try:
        user_info = client.users_info(user=user_id)
        user_name = user_info["user"]["real_name"]
    except SlackApiError as e:
        user_name = "Unknown User"
        logging.error(f"Error fetching user info: {e.response['error']}")
    
    
    # Post message to the channel with buttons
    try:
        result = client.chat_postMessage(
            channel=channel_id,
            blocks=[
                # Header block
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "New Swarm Request",
                        "emoji": True
                    }
                },
                # Section with inline fields for Ticket, Entitlement, Skill Group, Support Tier, and Priority
                {
                    "type": "section",
                    "block_id": "details-section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Ticket:*\n" + ticket
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Entitlement:*\n" + entitlement
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Skill Group:*\n" + skill_group
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Support Tier:*\n" + support_tier
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Priority:*\n" + priority
                        },
                        {
                            "type": "mrkdwn", 
                            "text": f"*Opened By:*\n<@{user_id}>"
                        }

                    ]
                },
                # Divider block to separate sections
                {
                    "type": "divider"
                },
                # Section with detailed description
                {
                    "type": "section",
                    "block_id": "description-section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Issue Description:*\n" + issue_description
                    }
                },
                {
                    "type": "section",
                    "block_id": "help-required-section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Help Required:*\n" + help_required
                    }
                },
                # Actions block
                {
                    "type": "actions",
                    "block_id": "actions-block",
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
        cur.execute("SELECT id FROM swarm_requests WHERE message_ts = %s", (message_ts,))
        existing_record = cur.fetchone()
        if existing_record:
            # Update the existing swarm request status to 'resolved'
            cur.execute("""
                UPDATE swarm_requests
                SET status = %s, updated_at = NOW()
                WHERE message_ts = %s
            """, ('resolved', message_ts))
        else:
            logging.error(f"No existing swarm request found for message_ts: {message_ts}")

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
        cur.execute("SELECT id FROM swarm_requests WHERE message_ts = %s", (message_ts,))
        existing_record = cur.fetchone()

        if existing_record:
            # Update the existing swarm request status to 'discarded'
            cur.execute("""
                UPDATE swarm_requests
                SET status = %s, updated_at = NOW()
                WHERE message_ts = %s
            """, ('discarded', message_ts))
        else:
            logging.error(f"No existing swarm request found for message_ts: {message_ts}")

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

        updated_blocks = [
            block for block in body["message"]["blocks"]
            if not (
                (block.get("type") == "section" and
                 ("Swarm request resolved by" in block.get("text", {}).get("text", "") or
                  "Swarm request discarded by" in block.get("text", {}).get("text", ""))) or
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
        '''cur.execute(
            """
            INSERT INTO swarm_requests (message_ts, status)
            VALUES (%s, 'reopened')
            ON CONFLICT (message_ts) DO UPDATE
            SET status = 'reopened', updated_at = CURRENT_TIMESTAMP
            """,
            (message_ts,)
        )'''

        # Fetch existing swarm request data using the message timestamp
        cur.execute("""
            SELECT ticket, entitlement, skill_group, support_tier, priority,
                   issue_description, help_required, user_id, channel_id
            FROM swarm_requests
            WHERE message_ts = %s
        """, (message_ts,))
        swarm_data = cur.fetchone()

        if not swarm_data:
            logging.error(f"Swarm request not found for message_ts: {message_ts}")
            conn.close()
            return

        # Ensure you have all data from the database
        ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required, user_id, channel_id = swarm_data

        # Update the status, preserving other fields
        cur.execute("""
            UPDATE swarm_requests
            SET status = %s,
                updated_at = NOW()
            WHERE message_ts = %s
        """, (new_status, message_ts))
        conn.commit()

        conn.commit()
        cur.close()
        conn.close()

    except SlackApiError as e:
        logging.error(f"Error reopening swarm request: {e.response['error']}")


def get_user_info(client, user_id):
    try:
        response = client.users_info(user=user_id)
        return response['user']['real_name']
    except SlackApiError as e:
        logging.error(f"Error fetching user info: {e.response['error']}")
        return user_id  # Return the user_id if fetching fails



@app.event("app_home_opened")
def app_home_opened(client, event):
    user_id = event["user"]

    try:
        # Fetch user info to get the real name
        user_info = client.users_info(user=user_id)
        user_name = user_info["user"]["real_name"]

        # Query the database to get total statistics
        conn = get_db_connection()
        cur = conn.cursor()

        # Get total counts
        cur.execute("""
            SELECT
                COUNT(*) AS total_requests,
                COUNT(*) FILTER (WHERE status = 'open') AS total_open,
                COUNT(*) FILTER (WHERE status = 'resolved') AS total_resolved,
                COUNT(*) FILTER (WHERE status = 'discarded') AS total_discarded
            FROM swarm_requests
        """)
        stats = cur.fetchone()

        if stats:
            total_requests, total_open, total_resolved, total_discarded = stats
        else:
            total_requests = total_open = total_resolved = total_discarded = 0
        
        # Prepare statistics for display
        blocks = [
            {
                "type": "section",
                "block_id": "total_swarm_requests",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Swarm Requests:* {total_requests}"
                }
            },
            {
                "type": "section",
                "block_id": "total_open_requests",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Open Requests:* {total_open}"
                }
            },
            {
                "type": "section",
                "block_id": "total_resolved_requests",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Resolved Requests:* {total_resolved}"
                }
            },
            {
                "type": "section",
                "block_id": "total_discarded_requests",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Discarded Requests:* {total_discarded}"
                }
            },
            {"type": "divider"}
        ]

        # Query to get the request counts by user
        cur.execute("""
            SELECT 
                user_id,
                COUNT(*) AS total_requests,
                COUNT(*) FILTER (WHERE status = 'open') AS total_open,
                COUNT(*) FILTER (WHERE status = 'resolved') AS total_resolved,
                COUNT(*) FILTER (WHERE status = 'discarded') AS total_discarded
            FROM swarm_requests
            GROUP BY user_id
        """)
        user_requests = cur.fetchall()
        conn.close()

        # Fetch user information for all users involved
        user_names = {}
        for uid, _, _, _, _ in user_requests:
            try:
                user_info = client.users_info(user=uid)
                user_names[uid] = user_info["user"]["real_name"]
            except SlackApiError:
                user_names[uid] = f"<@{uid}>"  # Fallback to mention format

        # Add user-level statistics blocks
        for uid, total, open_count, resolved_count, discarded_count in user_requests:
            user_name_display = user_names.get(uid, f"<@{uid}>")
            blocks.append(
                {
                    "type": "section",
                    "block_id": f"user_{uid}_stats",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{user_name_display}*:\n"
                                f"- Total Requests: {total}\n"
                                f"- Open: {open_count}\n"
                                f"- Resolved: {resolved_count}\n"
                                f"- Discarded: {discarded_count}"
                    }
                }
            )
            blocks.append({"type": "divider"})  # Divider between user stats

        # Update the App Home tab
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )

    except SlackApiError as e:
        logging.error(f"Error opening app home: {e.response['error']}")

# Start the app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))