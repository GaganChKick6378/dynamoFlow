import boto3
from typing import Dict, Any, List, Optional
from langflow import CustomComponent

class DynamoDBHandler:
    # ... (rest of the handler class, no changes needed here) ...
    def __init__(self, region_name: str):
        self.dynamodb      = boto3.resource("dynamodb", region_name=region_name)
        self.bugs_table    = self.dynamodb.Table("BUGS")
        self.blocked_table = self.dynamodb.Table("BLOCKED")
        self.tasks_table   = self.dynamodb.Table("TASKS")

    def get_items_by_channel(self, channel_id: str, category: str) -> List[Dict[str, Any]]:
        table = getattr(self, f"{category.lower()}_table")
        resp  = table.get_item(Key={"channel_id": channel_id})
        return resp.get("Item", {}).get("items", [])

    def update_item(self, table_name: str, channel_id: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        table = getattr(self, f"{table_name.lower()}_table")
        resp  = table.get_item(Key={"channel_id": channel_id})
        items = resp.get("Item", {}).get("items", [])
        for it in items:
            if it.get("id") == item_id:
                it.update(updates)
                break
        updated = table.update_item(
            Key={"channel_id": channel_id},
            UpdateExpression="SET items = :items",
            ExpressionAttributeValues={":items": items},
            ReturnValues="ALL_NEW"
        )
        return updated.get("Attributes", {})

    def append_message(self, table_name: str, channel_id: str, new_item: Dict[str, Any]) -> Dict[str, Any]:
        table = getattr(self, f"{table_name.lower()}_table")
        resp  = table.get_item(Key={"channel_id": channel_id})
        items = resp.get("Item", {}).get("items", [])
        items.append(new_item)
        updated = table.update_item(
            Key={"channel_id": channel_id},
            UpdateExpression="SET items = :items",
            ExpressionAttributeValues={":items": items},
            ReturnValues="ALL_NEW"
        )
        return updated.get("Attributes", {})

    def create_channel_if_not_exists(self, table_name: str, channel_id: str) -> Dict[str, Any]:
        table = getattr(self, f"{table_name.lower()}_table")
        resp  = table.get_item(Key={"channel_id": channel_id})
        if "Item" not in resp:
            table.put_item(Item={"channel_id": channel_id, "items": []})
            return {"status": "created"}
        return {"status": "exists"}


class DynamoDBComponent(CustomComponent):
    display_name = "DynamoDB Component"
    description  = "CRUD on BUGS, BLOCKED or TASKS tables"

    # THIS METHOD CREATES THE INPUT FIELDS.
    # If they are not showing up, Langflow has not loaded this new code.
    def build_config(self):
        return {
            "region_name": {"type": "str", "required": True, "display_name": "AWS Region"},
            "operation":   {"type": "str", "required": True, "display_name": "Operation"},
            "table_name":  {"type": "str", "required": True, "display_name": "Table Name"},
            "channel_id":  {"type": "str", "required": True, "display_name": "Channel ID"},
            "item_id":     {"type": "str", "required": False, "display_name": "Item ID"},
            "updates":     {"type": "dict", "required": False, "display_name": "Updates"},
            "new_item":    {"type": "dict", "required": False, "display_name": "New Item"},
        }

    # This method is called when the component runs.
    def build(
        self,
        region_name: str,
        operation: str,
        table_name: str,
        channel_id: str,
        item_id: Optional[str] = None,
        updates: Optional[Dict[str, Any]] = None,
        new_item: Optional[Dict[str, Any]] = None
    ) -> Any:
        handler = DynamoDBHandler(region_name)
        op = operation.lower()
        if op == "create_channel":
            return handler.create_channel_if_not_exists(table_name, channel_id)
        if op == "get_items":
            return {"items": handler.get_items_by_channel(channel_id, table_name)}
        if op == "update_item":
            if not item_id or updates is None:
                raise ValueError("For 'update_item' operation, 'item_id' and 'updates' are required.")
            return handler.update_item(table_name, channel_id, item_id, updates)
        if op == "append_item":
            if new_item is None:
                 raise ValueError("For 'append_item' operation, 'new_item' is required.")
            return handler.append_message(table_name, channel_id, new_item)
        raise ValueError(f"Unsupported operation: {operation}")