import os
import psycopg2
from urllib.parse import urlparse
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

# Initialize the Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize the WebClient
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Database connection
def get_db_connection():
    url = urlparse(os.environ.get("DATABASE_URL"))
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return conn

# Open the modal
@app.command("/swarmrequest")
def handle_swarm_request(ack, body):
    ack()
    trigger_id = body.get("trigger_id")
    
    if not trigger_id:
        print("Error: Missing trigger_id")
        return

    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "swarm_request_form",
                "title": {
                    "type": "plain_text",
                    "text": "Swarm Request"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "ticket_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Ticket"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "ticket_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "entitlement_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Entitlement"
                        },
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
                        "block_id": "skill_group_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Skill Group"
                        },
                        "element": {
                            "type": "static_select",
                            "action_id": "skill_group_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Data"}, "value": "data"},
                                {"text": {"type": "plain_text", "text": "Runtime"}, "value": "runtime"},
                                {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "platform"},
                                {"text": {"type": "plain_text", "text": "Account Management"}, "value": "account_management"},
                                {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                            ]
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "support_tier_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Support Tier"
                        },
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
                        "block_id": "priority_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Priority"
                        },
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
                        "block_id": "issue_description_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Issue Description"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "multiline": True,
                            "action_id": "issue_description_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "help_required_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Help Required"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "multiline": True,
                            "action_id": "help_required_input"
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "submit_block",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Submit"
                                },
                                "action_id": "submit_button"
                            }
                        ]
                    }
                ]
            }
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")

# Handle modal submissions
@app.view("swarm_request_form")
def handle_modal_submission(ack, body):
    ack()
    try:
        values = body["view"]["state"]["values"]
        ticket = values["ticket_block"]["ticket_input"]["value"]
        entitlement = values["entitlement_block"]["entitlement_select"]["selected_option"]["value"]
        skill_group = values["skill_group_block"]["skill_group_select"]["selected_option"]["value"]
        support_tier = values["support_tier_block"]["support_tier_select"]["selected_option"]["value"]
        priority = values["priority_block"]["priority_select"]["selected_option"]["value"]
        issue_description = values["issue_description_block"]["issue_description_input"]["value"]
        help_required = values["help_required_block"]["help_required_input"]["value"]

        # Save to database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO swarm_requests (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (ticket, entitlement, skill_group, support_tier, priority, issue_description, help_required)
        )
        conn.commit()
        cur.close()
        conn.close()

        # Post a confirmation message to the same channel
        user_id = body["user"]["id"]
        # You may want to change this to a specific channel or dynamically get the channel from the body
        client.chat_postMessage(
            channel=body["user"]["id"],  # Adjust based on actual channel information
            text=f"Thank you <@{user_id}>! Your swarm request has been submitted."
        )
    except KeyError as e:
        print(f"Error processing submission: {e}")

# Handle app home page view
@app.event("app_home_opened")
def handle_app_home_opened(event, client):
    user_id = event["user"]
    try:
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "block_id": "welcome_block",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to the Swarm Request App!*"
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "actions_block",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Create Request"
                                },
                                "action_id": "create_request_button"
                            }
                        ]
                    }
                ]
            }
        )
    except SlackApiError as e:
        print(f"Error publishing view: {e.response['error']}")

# Handle button click to open the form
@app.action("create_request_button")
def handle_create_request_button(ack, body):
    ack()
    trigger_id = body.get("trigger_id")
    
    if not trigger_id:
        print("Error: Missing trigger_id")
        return

    try:
        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "swarm_request_form",
                "title": {
                    "type": "plain_text",
                    "text": "Swarm Request"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "ticket_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Ticket"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "ticket_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "entitlement_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Entitlement"
                        },
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
                        "block_id": "skill_group_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Skill Group"
                        },
                        "element": {
                            "type": "static_select",
                            "action_id": "skill_group_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Data"}, "value": "data"},
                                {"text": {"type": "plain_text", "text": "Runtime"}, "value": "runtime"},
                                {"text": {"type": "plain_text", "text": "Platform/Web Services"}, "value": "platform"},
                                {"text": {"type": "plain_text", "text": "Account Management"}, "value": "account_management"},
                                {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                            ]
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "support_tier_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Support Tier"
                        },
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
                        "block_id": "priority_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Priority"
                        },
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
                        "block_id": "issue_description_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Issue Description"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "multiline": True,
                            "action_id": "issue_description_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "help_required_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Help Required"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "multiline": True,
                            "action_id": "help_required_input"
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "submit_block",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Submit"
                                },
                                "action_id": "submit_button"
                            }
                        ]
                    }
                ]
            }
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")

# Start the app
if __name__ == "__main__":
    import socket_mode
    import slack_sdk
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    handler = socket_mode.AppHandler(
        app=app,
        client=client
    )
    
    app.start(port=int(os.environ.get("PORT", 3000)))
