from typing import Dict, Any, List, Optional
from langflow import CustomComponent
from langflow.field_config import FieldConfig
import boto3

class DynamoDBComponent(CustomComponent):
    display_name = "DynamoDB Component"
    description = "Handles DynamoDB operations for message processing"

    def build_config(self):
        return {
            "region_name": {"type": "str", "required": True},
            "operation": {"type": "str", "required": True},
            "table_name": {"type": "str", "required": True},
            "channel_id": {"type": "str", "required": True},
            "item_id": {"type": "str", "required": False},
            "updates": {"type": "dict", "required": False},
            "new_item": {"type": "dict", "required": False}
        }

    def build(
        self,
        region_name: str,
        operation: str,
        table_name: str,
        channel_id: str,
        item_id: Optional[str] = None,
        updates: Optional[Dict[str, Any]] = None,
        new_item: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        table = dynamodb.Table(table_name)

        if operation == "get_items":
            response = table.get_item(
                Key={"channel_id": channel_id}
            )
            return {"items": response.get("Item", {}).get("items", [])}

        elif operation == "update_item":
            if not item_id or not updates:
                raise ValueError("item_id and updates are required for update_item operation")
            
            # Get existing items
            response = table.get_item(Key={"channel_id": channel_id})
            items = response.get("Item", {}).get("items", [])
            
            # Update the specific item
            for item in items:
                if item["id"] == item_id:
                    item.update(updates)
                    break
            
            # Update the table
            table.put_item(
                Item={
                    "channel_id": channel_id,
                    "items": items
                }
            )
            return {"result": {"channel_id": channel_id, "items": items}}

        elif operation == "append_message":
            if not new_item:
                raise ValueError("new_item is required for append_message operation")
            
            # Get existing items
            response = table.get_item(Key={"channel_id": channel_id})
            items = response.get("Item", {}).get("items", [])
            
            # Append new item
            items.append(new_item)
            
            # Update the table
            table.put_item(
                Item={
                    "channel_id": channel_id,
                    "items": items
                }
            )
            return {"result": {"channel_id": channel_id, "items": items}}

        else:
            raise ValueError(f"Unsupported operation: {operation}")

class DynamoDBHandler:
    def __init__(self, region_name: str = "us-west-2"):
        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.bugs_table = self.dynamodb.Table("BUGS")
        self.blocked_table = self.dynamodb.Table("BLOCKED")
        self.tasks_table = self.dynamodb.Table("TASKS")

    def get_items_by_channel(self, channel_id: str, category: str) -> List[Dict[str, Any]]:
        """Retrieve items from the specified table for a given channel_id."""
        table = getattr(self, f"{category.lower()}_table")
        try:
            response = table.get_item(Key={"channel_id": channel_id})
            return response.get("Item", {}).get("items", [])
        except Exception as e:
            print(f"Error retrieving items: {e}")
            return []

    def update_item(self, table_name: str, channel_id: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an item in the specified table."""
        table = getattr(self, f"{table_name.lower()}_table")
        try:
            # First get the current items
            response = table.get_item(Key={"channel_id": channel_id})
            items = response.get("Item", {}).get("items", [])
            
            # Find and update the specific item
            for item in items:
                if item["id"] == item_id:
                    item.update(updates)
                    break
            
            # Update the entire items list
            response = table.update_item(
                Key={"channel_id": channel_id},
                UpdateExpression="SET items = :items",
                ExpressionAttributeValues={":items": items},
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes", {})
        except Exception as e:
            print(f"Error updating item: {e}")
            return {}

    def append_message(self, table_name: str, channel_id: str, new_item: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new item to the channel's items list."""
        table = getattr(self, f"{table_name.lower()}_table")
        try:
            # First get the current items
            response = table.get_item(Key={"channel_id": channel_id})
            items = response.get("Item", {}).get("items", [])
            
            # Append the new item
            items.append(new_item)
            
            # Update the entire items list
            response = table.update_item(
                Key={"channel_id": channel_id},
                UpdateExpression="SET items = :items",
                ExpressionAttributeValues={":items": items},
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes", {})
        except Exception as e:
            print(f"Error appending message: {e}")
            return {}

    def create_channel_if_not_exists(self, table_name: str, channel_id: str) -> None:
        """Create a new channel entry if it doesn't exist."""
        table = getattr(self, f"{table_name.lower()}_table")
        try:
            # Check if channel exists
            response = table.get_item(Key={"channel_id": channel_id})
            if "Item" not in response:
                # Create new channel with empty items list
                table.put_item(Item={
                    "channel_id": channel_id,
                    "items": []
                })
        except Exception as e:
            print(f"Error creating channel: {e}") 