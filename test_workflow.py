import json
import os
from dotenv import load_dotenv
from custom_components.message_processor_component import MessageProcessorComponent
from custom_components.dynamodb_component import DynamoDBComponent

# Load environment variables
load_dotenv()

def test_message_processing():
    # Test input
    test_input = {
        "message": "Found a critical bug in the login system where users can't authenticate",
        "category": "BUGS",
        "channel_id": "C1234567890",
        "api_key": os.getenv("OPENAI_API_KEY")
    }
    
    # Load the workflow
    with open("workflows/message_processing_flow.json", "r") as f:
        workflow = json.load(f)
    
    print("Workflow loaded successfully!")
    print("\nTest Input:")
    print(json.dumps(test_input, indent=2))
    
    print("\nTo test this workflow:")
    print("1. Start Langflow:")
    print("   cd langflow-langsmith")
    print("   docker-compose up")
    print("\n2. Open http://localhost:7860 in your browser")
    print("\n3. Import the workflow from workflows/message_processing_flow.json")
    print("\n4. Use the test input above to run the workflow")
    print("\nExpected Output:")
    print("""
    {
        "processed_result": {
            "id": "bugs_[timestamp]",
            "message": "Found a critical bug in the login system where users can't authenticate",
            "status": 0,
            "created_timestamp": "[timestamp]",
            "updated_timestamp": "[timestamp]"
        },
        "is_update": false,
        "db_result": {
            "channel_id": "C1234567890",
            "items": [
                {
                    "id": "bugs_[timestamp]",
                    "message": "Found a critical bug in the login system where users can't authenticate",
                    "status": 0,
                    "created_timestamp": "[timestamp]",
                    "updated_timestamp": "[timestamp]"
                }
            ]
        }
    }
    """)

def test_message_processor():
    # Test MessageProcessorComponent
    processor = MessageProcessorComponent()
    result = processor.build(
        api_key="test_key",
        message="There's a bug in the login page",
        category="BUGS",
        channel_id="test_channel",
        existing_items=[]
    )
    print("Message Processor Test Result:", result)
    return result

def test_dynamodb():
    # Test DynamoDBComponent
    dynamo = DynamoDBComponent()
    result = dynamo.build(
        region_name="us-west-2",
        operation="get_items",
        table_name="BUGS",
        channel_id="test_channel"
    )
    print("DynamoDB Test Result:", result)
    return result

if __name__ == "__main__":
    print("Testing Message Processor Component...")
    test_message_processor()
    
    print("\nTesting DynamoDB Component...")
    test_dynamodb()

    test_message_processing() 