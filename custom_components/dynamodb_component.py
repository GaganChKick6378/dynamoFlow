import boto3
from typing import Dict, Any, List, Optional
from langflow.custom import Component
from langflow.io import StrInput, DropdownInput, DataInput, Output, SecretStrInput
from langflow.schema import Data
from datetime import datetime

class DynamoDBHandler:
    """Handles all direct communication with AWS DynamoDB."""
    def __init__(self, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
        """Initializes the DynamoDB resource with provided credentials."""
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self.bugs_table    = self.dynamodb.Table("BUGS")
        self.blocked_table = self.dynamodb.Table("BLOCKED")
        self.tasks_table   = self.dynamodb.Table("TASKS")

    def get_channel_messages(self, channel_id: str, category: str) -> List[Dict[str, Any]]:
        """Get all messages for a channel."""
        table = getattr(self, f"{category.lower()}_table")
        resp = table.get_item(Key={"channel_id": channel_id})
        return resp.get("Item", {}).get("messages", [])

    def update_message(self, table_name: str, channel_id: str, message_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a specific message in the channel's message list."""
        table = getattr(self, f"{table_name.lower()}_table")
        resp = table.get_item(Key={"channel_id": channel_id})
        messages = resp.get("Item", {}).get("messages", [])
        
        # Find and update the message
        message_updated = False
        for message in messages:
            if message.get("id") == message_id:
                message.update(updates)
                message_updated = True
                break
        
        if not message_updated:
            raise ValueError(f"Message with ID {message_id} not found")
        
        # Update the item with the modified message list
        updated = table.update_item(
            Key={"channel_id": channel_id},
            UpdateExpression="SET messages = :messages",
            ExpressionAttributeValues={":messages": messages},
            ReturnValues="ALL_NEW"
        )
        return updated.get("Attributes", {})

    def append_message(self, table_name: str, channel_id: str, new_message: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new message to the channel's message list."""
        table = getattr(self, f"{table_name.lower()}_table")
        
        # Get existing messages or initialize empty list
        resp = table.get_item(Key={"channel_id": channel_id})
        messages = resp.get("Item", {}).get("messages", [])
        
        # Add new message to the list
        messages.append(new_message)
        
        # Update the item with the new message list
        updated = table.update_item(
            Key={"channel_id": channel_id},
            UpdateExpression="SET messages = :messages",
            ExpressionAttributeValues={":messages": messages},
            ReturnValues="ALL_NEW"
        )
        return updated.get("Attributes", {})

    def create_channel_if_not_exists(self, table_name: str, channel_id: str) -> Dict[str, Any]:
        """Create a new channel with an empty message list if it doesn't exist."""
        table = getattr(self, f"{table_name.lower()}_table")
        resp = table.get_item(Key={"channel_id": channel_id})
        if "Item" not in resp:
            table.put_item(Item={"channel_id": channel_id, "messages": []})
            return {"status": "created"}
        return {"status": "exists"}

class DynamoDBComponent(Component):
    display_name = "DynamoDB Component"
    description  = "Stores messages in DynamoDB as a list under a channel ID."
    icon = "database"

    inputs = [
        SecretStrInput(name="aws_access_key_id", display_name="AWS Access Key ID", required=True),
        SecretStrInput(name="aws_secret_access_key", display_name="AWS Secret Access Key", required=True),
        StrInput(name="region_name", display_name="AWS Region", value="us-east-1", required=True),
        DataInput(
            name="message_data",
            display_name="Message Data",
            info="JSON containing operation, channel_id, message, category, datetime, urls, and file_urls",
            required=True
        )
    ]

    outputs = [
        Output(display_name="Result", name="result", method="run_operation")
    ]

    def validate_urls(self, urls: List[str]) -> bool:
        """Validates that all URLs in the list are valid."""
        if not isinstance(urls, list):
            return False
        # Basic URL validation - you might want to add more sophisticated validation
        for url in urls:
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                return False
        return True

    def run_operation(self) -> Data:
        """
        This is the main execution method for the component.
        Processes the input JSON and performs the requested operation.
        """
        # Access the inputs provided in the UI or from connected components
        region_name = self.region_name
        message_data = self.message_data.data
        
        # Validate required fields
        required_fields = ["operation", "channel_id", "category"]
        for field in required_fields:
            if field not in message_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Extract data from the input JSON
        operation = message_data["operation"].lower()
        channel_id = message_data["channel_id"]
        category = message_data["category"].upper()
        
        # Validate category
        valid_categories = ["BUGS", "BLOCKED", "TASKS"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
        handler = DynamoDBHandler(
            region_name=region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

        result_data = {}
        
        if operation == "get_items":
            messages = handler.get_channel_messages(channel_id, category)
            result_data = {"messages": messages}
            
        elif operation == "update_item":
            if "message_id" not in message_data or "updates" not in message_data:
                raise ValueError("For 'update_item', 'message_id' and 'updates' are required.")
            
            # Validate updates
            updates = message_data["updates"]
            if not isinstance(updates, dict):
                raise ValueError("Updates must be a dictionary")
            
            # Handle datetime in updates if present
            if "datetime" in updates:
                try:
                    datetime.fromisoformat(updates["datetime"].replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError("Invalid datetime format in updates. Use ISO format (YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM])")
            
            # Validate URLs in updates if present
            if "urls" in updates and not self.validate_urls(updates["urls"]):
                raise ValueError("Invalid urls format in updates")
            if "file_urls" in updates and not self.validate_urls(updates["file_urls"]):
                raise ValueError("Invalid file_urls format in updates")
            
            result_data = handler.update_message(category, channel_id, message_data["message_id"], updates)
            
        elif operation == "append_item":
            if "message" not in message_data:
                raise ValueError("For 'append_item', 'message' is required.")
            
            # Handle optional fields with defaults
            datetime_str = message_data.get("datetime")
            if datetime_str:
                try:
                    datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError("Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM])")
            else:
                datetime_str = datetime.utcnow().isoformat() + 'Z'

            # Validate URLs if provided
            urls = message_data.get("urls", [])
            if not self.validate_urls(urls):
                raise ValueError("Invalid urls format. Must be a list of valid URLs starting with http:// or https://")

            # Validate file URLs if provided
            file_urls = message_data.get("file_urls", [])
            if not self.validate_urls(file_urls):
                raise ValueError("Invalid file_urls format. Must be a list of valid URLs starting with http:// or https://")
            
            # Create channel if it doesn't exist
            handler.create_channel_if_not_exists(category, channel_id)
            
            # Get existing messages to determine the new message ID
            existing_messages = handler.get_channel_messages(channel_id, category)
            
            # Prepare the new message
            new_message = {
                "id": str(len(existing_messages) + 1),
                "message": message_data["message"],
                "datetime": datetime_str,
                "urls": urls,
                "file_urls": file_urls,
                "timestamp": str(boto3.client('dynamodb').get_current_time())
            }
            
            result_data = handler.append_message(category, channel_id, new_message)
            
        else:
            raise ValueError(f"Unsupported operation: {operation}. Must be one of: get_items, update_item, append_item")
        
        self.status = result_data
        return Data(data=result_data)
