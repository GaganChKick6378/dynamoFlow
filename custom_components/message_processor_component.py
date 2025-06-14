import openai
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from langflow import CustomComponent

class MessageProcessor:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def _get_embedding(self, text: str) -> List[float]:
        resp = openai.embeddings.create(input=[text], model="text-embedding-ada-002")
        return resp.data[0].embedding

    def _cosine(self, a: List[float], b: List[float]) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def find_similar_message(
        self,
        new_message: str,
        existing: List[Dict[str, Any]],
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        emb_new = self._get_embedding(new_message)
        for item in existing:
            sim = self._cosine(emb_new, self._get_embedding(item["message"]))
            if sim >= threshold:
                return item
        return None

    def determine_status(self, message: str) -> int:
        prompt = (
            "You are a status analyzer. Return only 0 (new issue) or 2 (resolved).\n"
            f"Message: {message}"
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
        )
        try:
            val = int(resp.choices[0].message.content.strip())
            return 2 if val == 2 else 0
        except:
            return 0

    def process_message(
        self,
        message: str,
        category: str,
        channel_id: str,
        existing_items: List[Dict[str, Any]],
        threshold: float
    ) -> Tuple[Dict[str, Any], bool]:
        similar = self.find_similar_message(message, existing_items, threshold)
        if similar:
            new_status = self.determine_status(message)
            if new_status != similar.get("status"):
                return (
                    {
                        "id": similar["id"],
                        "status": new_status,
                        "updated_timestamp": datetime.utcnow().isoformat(),
                    },
                    True,
                )
        now = datetime.utcnow().isoformat()
        return (
            {
                "id": f"{category.lower()}_{datetime.utcnow().timestamp()}",
                "message": message,
                "status": self.determine_status(message),
                "created_timestamp": now,
                "updated_timestamp": now,
            },
            False,
        )

class MessageProcessorComponent(CustomComponent):
    display_name = "Message Processor Component"
    description  = "Embedding + similarity + GPT status classification"

    def build_config(self):
        return {
            "api_key":              {"type": "str",   "required": True},
            "message":              {"type": "str",   "required": True},
            "category":             {"type": "str",   "required": True},
            "channel_id":           {"type": "str",   "required": True},
            "existing_items":       {"type": "list",  "required": True},
            "similarity_threshold": {"type": "float", "required": True},
        }

    def build(
        self,
        api_key: str,
        message: str,
        category: str,
        channel_id: str,
        existing_items: List[Dict[str, Any]],
        similarity_threshold: float,
        **kwargs,  # catches the Code-Mode 'code' arg
    ) -> Dict[str, Any]:
        proc = MessageProcessor(api_key)
        result, is_update = proc.process_message(
            message, category, channel_id, existing_items, similarity_threshold
        )
        return {"result": result, "is_update": is_update}