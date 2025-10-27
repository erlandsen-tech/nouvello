"""
AWS Bedrock Integration for AI Chapter Detection
Supports multiple LLM providers including Bedrock, OpenAI, and local models
"""

import json
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time

# Optional imports for different providers
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

try:
    import openai
except ImportError:
    openai = None

@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, region: Optional[str] = None):
        self.api_key = api_key
        self.region = region
    
    def generate_response(self, prompt: str, model: str = None) -> LLMResponse:
        """Generate response from LLM"""
        raise NotImplementedError

class BedrockProvider(LLMProvider):
    """AWS Bedrock provider"""
    
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        super().__init__(region=region)
        self.profile = profile
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Bedrock client"""
        if not boto3:
            raise ImportError("boto3 is required for Bedrock. Install with: pip install boto3")
        
        try:
            if self.profile:
                session = boto3.Session(profile_name=self.profile)
                self.client = session.client('bedrock-runtime', region_name=self.region)
            else:
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
            
            max_retries = 1  # Single retry to keep it fast
            retry_delay = 1
            timeout_seconds = 15  # 15 second timeout per request
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Bedrock API request timed out")
            
            for attempt in range(max_retries):
                try:
                    # Set timeout
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_seconds)
                    
                    response = self.client.invoke_model(
                        modelId=model,
                        body=json.dumps(body),
                        contentType="application/json"
                    )
                    
                    # Cancel timeout
                    signal.alarm(0)
                    break  # Success, exit retry loop
                    
                except TimeoutError:
                    signal.alarm(0)  # Cancel timeout
                    if attempt < max_retries - 1:
                        print(f"Bedrock API request timed out (attempt {attempt + 1}). Retrying...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise Exception("Bedrock API request timed out after all retries")
                except Exception as e:
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

class OpenAIProvider(LLMProvider):
    """OpenAI provider"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key=api_key)
        if not openai:
            raise ImportError("openai is required. Install with: pip install openai")
        openai.api_key = api_key
    
    def generate_response(self, prompt: str, model: str = "gpt-3.5-turbo") -> LLMResponse:
        """Generate response using OpenAI"""
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                provider="openai",
                model=model,
                tokens_used=response.usage.total_tokens,
                cost=self._calculate_cost(response.usage.total_tokens, model)
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate approximate cost based on token usage"""
        pricing = {
            "gpt-3.5-turbo": 0.002 / 1000,  # $0.002 per 1K tokens
            "gpt-4": 0.03 / 1000,           # $0.03 per 1K tokens
        }
        return tokens * pricing.get(model, 0.002 / 1000)

class LocalProvider(LLMProvider):
    """Local model provider (for future implementation)"""
    
    def generate_response(self, prompt: str, model: str = "local") -> LLMResponse:
        """Generate response using local model"""
        # Placeholder for local model integration
        return LLMResponse(
            content="Local model not implemented yet",
            provider="local",
            model=model
        )

class MultiProviderLLM:
    """Multi-provider LLM client that can switch between providers"""
    
    def __init__(self, 
                 provider: str = "bedrock",
                 api_key: Optional[str] = None,
                 region: Optional[str] = None,
                 profile: Optional[str] = None):
        self.provider_name = provider
        self.provider = self._initialize_provider(provider, api_key, region, profile)
    
    def _initialize_provider(self, provider: str, api_key: Optional[str], 
                          region: Optional[str], profile: Optional[str]) -> LLMProvider:
        """Initialize the specified provider"""
        if provider.lower() == "bedrock":
            return BedrockProvider(region=region or "us-east-1", profile=profile)
        elif provider.lower() == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAIProvider(api_key)
        elif provider.lower() == "local":
            return LocalProvider()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate_response(self, prompt: str, model: str = None) -> LLMResponse:
        """Generate response using the configured provider"""
        if not model:
            model = self._get_default_model()
        
        return self.provider.generate_response(prompt, model)
    
    def _get_default_model(self) -> str:
        """Get default model for the current provider"""
        defaults = {
            "bedrock": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Use Claude Sonnet 4.5 inference profile
            "openai": "gpt-4",
            "local": "local"
        }
        return defaults.get(self.provider_name, "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models for the current provider"""
        if self.provider_name == "bedrock":
            return [
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
                "meta.llama2-13b-chat-v1",
                "meta.llama2-70b-chat-v1",
                "amazon.titan-text-express-v1",
                "amazon.titan-text-lite-v1"
            ]
        elif self.provider_name == "openai":
            return [
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo"
            ]
        else:
            return ["local"]

def test_bedrock_integration():
    """Test Bedrock integration"""
    print("🧪 Testing AWS Bedrock Integration")
    print("=" * 40)
    
    try:
        # Test Bedrock
        llm = MultiProviderLLM(provider="bedrock", region="us-east-1")
        
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
        ("openai", "OpenAI"),
    ]
    
    for provider, name in providers_to_test:
        print(f"\n🔧 Testing {name}...")
        try:
            if provider == "bedrock":
                llm = MultiProviderLLM(provider="bedrock")
            elif provider == "openai":
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    print(f"⚠️  Skipping {name} - no API key")
                    continue
                llm = MultiProviderLLM(provider="openai", api_key=api_key)
            
            models = llm.get_available_models()
            print(f"📋 Available models: {models[:3]}...")
            
        except Exception as e:
            print(f"❌ {name} failed: {e}")

if __name__ == "__main__":
    main()
