import os
from dotenv import load_dotenv
from custom_components.message_processor_component import MessageProcessorComponent
from custom_components.dynamodb_component import DynamoDBComponent

# Load environment variables
load_dotenv()

def test_components():
    # Test MessageProcessorComponent
    print("\nTesting MessageProcessorComponent...")
    processor = MessageProcessorComponent()
    message_result = processor.build(
        api_key=os.getenv("OPENAI_API_KEY"),
        message="There's a bug in the login page",
        category="BUGS",
        channel_id="test_channel",
        existing_items=[]
    )
    print("Message Processor Result:", message_result)

    # Test DynamoDBComponent
    print("\nTesting DynamoDBComponent...")
    dynamo = DynamoDBComponent()
    db_result = dynamo.build(
        region_name="us-west-2",
        operation="append_message",
        table_name="BUGS",
        channel_id="test_channel",
        new_item=message_result["result"]
    )
    print("DynamoDB Result:", db_result)

if __name__ == "__main__":
    test_components() 