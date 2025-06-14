from typing import Dict, Any, List, Optional
from langflow import CustomComponent
from langflow.field_config import FieldConfig
import openai
import numpy as np
from datetime import datetime

class MessageProcessorComponent(CustomComponent):
    display_name = "Message Processor Component"
    description = "Processes messages using OpenAI to determine status and updates"

    def build_config(self):
        return {
            "api_key": {"type": "str", "required": True},
            "message": {"type": "str", "required": True},
            "category": {"type": "str", "required": True},
            "channel_id": {"type": "str", "required": True},
            "existing_items": {"type": "list", "required": True}
        }

    def build(
        self,
        api_key: str,
        message: str,
        category: str,
        channel_id: str,
        existing_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        openai.api_key = api_key

        # Get embedding for the new message
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=message
        )
        new_embedding = response.data[0].embedding

        # Check if this is an update to an existing item
        is_update = False
        result = None

        for item in existing_items:
            # Get embedding for existing message
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=item["message"]
            )
            existing_embedding = response.data[0].embedding

            # Calculate similarity (dot product)
            similarity = sum(a * b for a, b in zip(new_embedding, existing_embedding))
            
            if similarity > 0.8:  # High similarity threshold
                is_update = True
                result = item
                break

        if not is_update:
            # Determine status for new message
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that determines the status of messages."},
                    {"role": "user", "content": f"Determine the status of this message (0 for new, 1 for in progress, 2 for resolved): {message}"}
                ]
            )
            status = int(response.choices[0].message.content.strip())

            # Create new item
            result = {
                "id": f"{category.lower()}_{hash(message)}",
                "message": message,
                "status": status,
                "created_timestamp": "2024-03-19T12:00:00Z",  # You might want to use actual timestamps
                "updated_timestamp": "2024-03-19T12:00:00Z"
            }

        return {
            "result": result,
            "is_update": is_update
        }

class MessageProcessor:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def _get_embedding(self, text: str) -> list:
        """Convert text to embedding vector using OpenAI's API (v1.x)."""
        response = openai.embeddings.create(
            input=[text],
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding

    def _calculate_similarity(self, embedding1: list, embedding2: list) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2)

    def find_similar_message(self, new_message: str, existing_messages: list, 
                           similarity_threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """Find if there's a similar message in the existing messages."""
        new_embedding = self._get_embedding(new_message)
        
        for item in existing_messages:
            existing_embedding = self._get_embedding(item['message'])
            similarity = self._calculate_similarity(new_embedding, existing_embedding)
            
            if similarity >= similarity_threshold:
                return item
        return None

    def determine_status(self, message: str) -> int:
        """Determine the status of a message using OpenAI."""
        prompt = f"""
        Analyze this message and determine if it's reporting a new issue or indicating completion.
        Message: {message}
        
        Return only:
        0 for new issue
        2 for completion/resolution
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a message classifier that determines if a message is reporting a new issue or indicating completion."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        return int(result) if result.isdigit() else 0

    def process_message(self, message: str, category: str, channel_id: str, 
                       existing_items: list) -> tuple[Dict[str, Any], bool]:
        """Process a message and determine if it's an update or new item."""
        similar_item = self.find_similar_message(message, existing_items)
        
        if similar_item:
            new_status = self.determine_status(message)
            if new_status != similar_item['status']:
                return {
                    'id': similar_item['id'],
                    'status': new_status,
                    'updated_timestamp': datetime.utcnow().isoformat()
                }, True
        
        return {
            'id': f"{category.lower()}_{datetime.utcnow().timestamp()}",
            'message': message,
            'status': self.determine_status(message),
            'created_timestamp': datetime.utcnow().isoformat(),
            'updated_timestamp': datetime.utcnow().isoformat()
        }, False 