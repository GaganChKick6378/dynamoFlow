import boto3
from typing import Dict, Any, List, Optional
from langflow.custom import Component
from langflow.io import StrInput, IntInput, FloatInput, MessageTextInput, Output, SecretStrInput, DataInput
from langflow.schema import Data

# The original Bedrock RAG logic is kept as a helper class for clarity.
# This class is not a Langflow component itself.
class BedrockKnowledgeBaseRAG:
    """A helper class to handle the Bedrock API communication."""
    def __init__(self, region_name: str, aws_access_key_id: str, aws_secret_access_key: str):
        """Initializes the Bedrock Knowledge Base client."""
        self.client = boto3.client(
            'bedrock-agent-runtime', 
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    
    def query(
        self,
        knowledge_base_id: str,
        question: str,
        model_arn: str,
        max_results: int,
        temperature: float
    ) -> Optional[Dict]:
        """Queries the knowledge base and generates a response."""
        try:
            request_params = {
                'retrieveAndGenerateConfiguration': {
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': knowledge_base_id,
                        'modelArn': model_arn,
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': max_results
                            }
                        },
                        'generationConfiguration': {
                            'inferenceConfig': {
                                'textInferenceConfig': {
                                    'temperature': temperature,
                                    'maxTokens': 2048,
                                    'stopSequences': ["\nObservation"]
                                }
                            }
                        }
                    }
                },
                'input': {
                    'text': question
                }
            }
            
            response = self.client.retrieve_and_generate(**request_params)
            return response
            
        except Exception as e:
            print(f"Error querying Bedrock: {str(e)}")
            return None

    def format_response(self, response: Optional[Dict]) -> Dict:
        """Formats the raw Bedrock response for easier use."""
        if not response:
            return {'answer': 'An error occurred while querying the knowledge base.', 'sources': []}
        
        answer = response.get('output', {}).get('text', 'No answer found.')
        sources = []
        
        if 'citations' in response:
            for citation in response['citations']:
                if 'retrievedReferences' in citation:
                    for ref in citation['retrievedReferences']:
                        source_info = {
                            'content': ref.get('content', {}).get('text', '')[:250] + '...',
                            'location': ref.get('location', {}),
                            'metadata': ref.get('metadata', {})
                        }
                        sources.append(source_info)
        
        return {'answer': answer, 'sources': sources}

# This is the Langflow component that will appear in the UI.
class BedrockKBComponent(Component):
    display_name = "Bedrock Knowledge Base"
    description = "Queries an AWS Bedrock Knowledge Base and generates a response."
    icon = "aws"

    # Define the input fields that will appear in the Langflow UI.
    inputs = [
        SecretStrInput(name="aws_access_key_id", display_name="AWS Access Key ID", required=True),
        SecretStrInput(name="aws_secret_access_key", display_name="AWS Secret Access Key", required=True),
        StrInput(name="region_name", display_name="AWS Region", value="us-west-2", required=True),
        StrInput(name="knowledge_base_id", display_name="Knowledge Base ID", required=True, info="The ID of the Bedrock Knowledge Base to query."),
        MessageTextInput(name="question", display_name="Question", info="The question to ask the knowledge base.", required=True),
        # Advanced parameters are hidden by default to keep the UI clean.
        StrInput(name="model_arn", display_name="Model ARN", value="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0", advanced=True),
        IntInput(name="max_results", display_name="Max Results", value=5, advanced=True),
        FloatInput(name="temperature", display_name="Temperature", value=0.0, advanced=True),
    ]

    # Define the output handles that other components can connect to.
    outputs = [
        Output(display_name="Answer", name="answer", method="get_answer"),
        Output(display_name="Sources", name="sources", method="get_sources")
    ]

    def _run_rag_query(self):
        """
        Helper method to run the query once and cache the result for all outputs.
        This prevents making multiple API calls if both 'Answer' and 'Sources' are connected.
        """
        # Check if we've already run the query for this execution
        if hasattr(self, "_rag_response"):
            return

        rag_handler = BedrockKnowledgeBaseRAG(
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

        raw_response = rag_handler.query(
            knowledge_base_id=self.knowledge_base_id,
            question=self.question,
            model_arn=self.model_arn,
            max_results=self.max_results,
            temperature=self.temperature
        )
        
        # Format the response and store it
        self._rag_response = rag_handler.format_response(raw_response)
        self.status = self._rag_response # Show the result in the component's status UI

    def get_answer(self) -> str:
        """This method is called when the 'Answer' output is connected."""
        self._run_rag_query()
        return self._rag_response.get("answer", "No answer found.")

    def get_sources(self) -> Data:
        """This method is called when the 'Sources' output is connected."""
        self._run_rag_query()
        sources_data = self._rag_response.get("sources", [])
        return Data(data=sources_data)
