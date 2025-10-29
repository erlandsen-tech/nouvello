"""
AWS Bedrock Integration for LLM responses
Bedrock-only client with a backward-compatible interface
"""

import json
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Optional imports for different providers
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

# Note: OpenAI support removed per project requirements

@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None

class LLMProvider:
    """Base class for LLM providers (kept for compatibility)"""
    
    def __init__(self, api_key: Optional[str] = None, region: Optional[str] = None):
        self.api_key = api_key
        self.region = region
    
    def generate_response(self, prompt: str, model: str = None) -> LLMResponse:
        raise NotImplementedError

class BedrockProvider(LLMProvider):
    """AWS Bedrock provider"""
    
    def __init__(self, region: str = "eu-central-1", profile: Optional[str] = None):
        # Allow region/profile to be provided via .env when not passed explicitly
        env_region = os.getenv("AWS_REGION")
        env_profile = os.getenv("AWS_PROFILE")
        effective_region = region or env_region or "eu-central-1"
        super().__init__(region=effective_region)
        self.profile = profile
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Bedrock client"""
        if not boto3:
            raise ImportError("boto3 is required for Bedrock. Install with: pip install boto3")
        
        try:
            # Prefer explicit AWS creds from environment if present (.env supported)
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            session_token = os.getenv("AWS_SESSION_TOKEN")

            # If a profile was not explicitly passed, fall back to env profile
            effective_profile = self.profile or os.getenv("AWS_PROFILE")

            if access_key and secret_key:
                session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token,
                    region_name=self.region
                )
                self.client = session.client('bedrock-runtime')
            elif effective_profile:
                session = boto3.Session(profile_name=effective_profile, region_name=self.region)
                self.client = session.client('bedrock-runtime')
            else:
                # Fall back to default credential chain (env, shared config, IAM role, etc.)
                self.client = boto3.client('bedrock-runtime', region_name=self.region)
        except Exception as e:
            raise Exception(f"Failed to initialize Bedrock client: {e}")
    
    def generate_response(self, prompt: str, model: str = "anthropic.claude-3-sonnet-20240229-v1:0") -> LLMResponse:
        """Generate response using Bedrock"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # Prepare the request body based on model
        if "claude" in model.lower():
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        elif "llama" in model.lower():
            body = {
                "prompt": prompt,
                "max_gen_len": 4000,
                "temperature": 0.1
            }
        else:
            # Generic format for other models
            body = {
                "prompt": prompt,
                "max_tokens": 4000,
                "temperature": 0.1
            }
        
        try:
            # Add timeout and retry logic
            import time
            import signal
            import threading
            
            max_retries = 1  # Single retry to keep it fast
            retry_delay = 1
            timeout_seconds = 15  # 15 second timeout per request
            
            # Check if we're in the main thread (signal only works there)
            is_main_thread = threading.current_thread() is threading.main_thread()
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Bedrock API request timed out")
            
            for attempt in range(max_retries):
                try:
                    # Set timeout only if in main thread (signal doesn't work in worker threads)
                    if is_main_thread:
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(timeout_seconds)
                    
                    response = self.client.invoke_model(
                        modelId=model,
                        body=json.dumps(body),
                        contentType="application/json"
                    )
                    
                    # Cancel timeout
                    if is_main_thread:
                        signal.alarm(0)
                    break  # Success, exit retry loop
                    
                except TimeoutError:
                    if is_main_thread:
                        signal.alarm(0)  # Cancel timeout
                    if attempt < max_retries - 1:
                        print(f"Bedrock API request timed out (attempt {attempt + 1}). Retrying...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise Exception("Bedrock API request timed out after all retries")
                except Exception as e:
                    if is_main_thread:
                        signal.alarm(0)  # Cancel timeout
                    if attempt < max_retries - 1:
                        print(f"Bedrock API attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise e  # Re-raise on final attempt
            
            response_body = json.loads(response['body'].read())
            
            # Extract content based on model type with validation
            content = ""
            if "claude" in model.lower():
                if 'content' in response_body and response_body['content']:
                    content = response_body['content'][0]['text']
                else:
                    raise Exception("Claude response missing content")
            elif "llama" in model.lower():
                content = response_body.get('generation', '')
            else:
                content = response_body.get('completion', str(response_body))
            
            # Validate content
            if not content or not content.strip():
                raise Exception("Empty response content from model")
            
            return LLMResponse(
                content=content.strip(),
                provider="bedrock",
                model=model,
                tokens_used=response_body.get('usage', {}).get('total_tokens'),
                cost=None  # Bedrock pricing varies by model
            )
            
        except ClientError as e:
            raise Exception(f"Bedrock API error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error with Bedrock: {e}")

## OpenAI provider removed

## Local provider removed for a lighter codebase

class MultiProviderLLM:
    """Bedrock-only LLM client (keeps the old interface for callers)"""
    
    def __init__(self, 
                 provider: str = "bedrock",
                 api_key: Optional[str] = None,
                 region: Optional[str] = None,
                 profile: Optional[str] = None):
        # provider/api_key kept for signature compatibility; Bedrock is always used
        self.provider_name = "bedrock"
        self.provider = BedrockProvider(region=region or "eu-central-1", profile=profile)
    
    def generate_response(self, prompt: str, model: str = None) -> LLMResponse:
        """Generate response using the configured provider"""
        if not model:
            model = self._get_default_model()
        
        return self.provider.generate_response(prompt, model)
    
    def _get_default_model(self) -> str:
        """Get default model (Bedrock)"""
        return "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Inference profile
    
    def get_available_models(self) -> List[str]:
        """Get list of available Bedrock models"""
        return [
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "meta.llama2-13b-chat-v1",
            "meta.llama2-70b-chat-v1",
            "amazon.titan-text-express-v1",
            "amazon.titan-text-lite-v1"
        ]

def test_bedrock_integration():
    """Test Bedrock integration"""
    print("🧪 Testing AWS Bedrock Integration")
    print("=" * 40)
    
    try:
        # Test Bedrock
        llm = MultiProviderLLM(provider="bedrock", region="eu-central-1")
        
        prompt = """
        Analyze this text and identify potential chapter boundaries.
        Look for clear topic shifts, chapter headings, or narrative breaks.
        
        Text: "Alice was beginning to get very tired. She sat by her sister on the bank. Suddenly, a white rabbit with pink eyes ran close by her."
        
        Return JSON with potential boundaries:
        {"boundaries": [{"text": "example", "confidence": 0.8, "reason": "topic shift"}]}
        """
        
        print("📡 Calling Bedrock Claude...")
        response = llm.generate_response(prompt)
        
        print(f"✅ Provider: {response.provider}")
        print(f"🤖 Model: {response.model}")
        print(f"📊 Tokens: {response.tokens_used}")
        print(f"💰 Cost: {response.cost}")
        print(f"📝 Response: {response.content[:200]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you have:")
        print("   - AWS credentials configured")
        print("   - Bedrock access enabled")
        print("   - boto3 installed: pip install boto3")

def main():
    """Main function to test different providers"""
    print("🚀 Multi-Provider LLM Test")
    print("=" * 30)
    
    # Test different providers
    providers_to_test = [
        ("bedrock", "AWS Bedrock"),
    ]
    
    for provider, name in providers_to_test:
        print(f"\n🔧 Testing {name}...")
        try:
            if provider == "bedrock":
                llm = MultiProviderLLM(provider="bedrock")
            # OpenAI support removed
            
            models = llm.get_available_models()
            print(f"📋 Available models: {models[:3]}...")
            
        except Exception as e:
            print(f"❌ {name} failed: {e}")

if __name__ == "__main__":
    main()
