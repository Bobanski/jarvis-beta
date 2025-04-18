import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

def test_parse_success():
    """Test successful parsing with o4-mini model"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    system_prompt = "Return a valid JSON object with fields: intent (string), location (string), and value (number)."
    user_prompt = "Turn on the lights"
    
    print("\n=== Testing successful JSON parsing ===")
    try:
        response = client.chat.completions.create(
            model="o4-mini-2025-04-16",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},  # Explicitly request JSON output
            temperature=0.7,  # Lower temperature for more predictable responses
            timeout=15  # Explicit timeout for cloud environments
        )
        
        # Our improved error handling with extensive checks
        if not response.choices or len(response.choices) == 0:
            print("❌ Error: OpenAI API returned empty choices")
            return False
            
        message = response.choices[0].message
        if not hasattr(message, 'content') or message.content is None:
            print("❌ Error: OpenAI API response missing content field")
            return False
            
        content = message.content.strip()
        print(f"Raw content:\n{content}")
        
        if not content:
            print("❌ Error: OpenAI API returned empty content")
            return False
        
        # Parse JSON
        try:
            parsed_data = json.loads(content)
            print(f"✅ Successfully parsed JSON:\n{json.dumps(parsed_data, indent=2)}")
            return True
        except json.JSONDecodeError as json_err:
            print(f"❌ Error parsing JSON: {str(json_err)}")
            print(f"Raw content causing error:\n{content}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_defensive_json_parsing():
    """Test our defensive JSON parsing strategies for Render environment"""
    print("\n=== Testing defensive JSON parsing ===")
    
    test_cases = [
        {
            "name": "Missing closing bracket",
            "content": '{ "intent": "set_color", "location": "bedroom"',
            "can_fix": True
        },
        {
            "name": "Single quotes instead of double quotes",
            "content": "{ 'intent': 'set_color', 'location': 'bedroom' }",
            "can_fix": True
        },
        {
            "name": "Missing quotes around property names",
            "content": "{ intent: 'set_color', location: 'bedroom' }",
            "can_fix": False  # This is harder to fix with simple methods
        },
        {
            "name": "Extra text before JSON",
            "content": "The result is: { \"intent\": \"set_color\", \"location\": \"bedroom\" }",
            "can_fix": False  # Hard to fix without complex parsing
        },
        {
            "name": "Extra text after JSON",
            "content": "{ \"intent\": \"set_color\", \"location\": \"bedroom\" } is the result",
            "can_fix": False
        },
        {
            "name": "Missing braces entirely",
            "content": "\"intent\": \"set_color\", \"location\": \"bedroom\"",
            "can_fix": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\nScenario: {test_case['name']}")
        content = test_case['content']
        print(f"Raw content: {content}")
        
        # Try standard parsing
        try:
            parsed = json.loads(content)
            print(f"✅ Standard parsing succeeded unexpectedly: {parsed}")
            continue
        except json.JSONDecodeError as e:
            print(f"⚠️ Standard parsing failed as expected: {str(e)}")
        
        # Try defensive parsing
        print("Attempting defensive parsing...")
        try:
            # Apply fixes similar to what we did in main.py
            clean_content = content.replace("'", '"')  # Replace single quotes with double quotes
            clean_content = clean_content.strip()
            
            # Extract JSON if there's text before or after
            import re
            json_pattern = r'({.*})'
            json_match = re.search(json_pattern, clean_content)
            if json_match:
                clean_content = json_match.group(1)
            
            # Ensure it starts and ends with braces
            if not clean_content.startswith('{'):
                clean_content = '{' + clean_content
            if not clean_content.endswith('}'):
                clean_content = clean_content + '}'
                
            print(f"After fixes: {clean_content}")
            fixed_parsed = json.loads(clean_content)
            print(f"✅ Defensive parsing succeeded: {json.dumps(fixed_parsed, indent=2)}")
        except json.JSONDecodeError as e:
            if test_case['can_fix']:
                print(f"❌ Defensive parsing failed unexpectedly: {str(e)}")
            else:
                print(f"ℹ️ Defensive parsing failed as expected for this difficult case: {str(e)}")

def simulate_error_handling():
    """Simulate different error scenarios to test our error handling"""
    print("\n=== Testing error handling with simulated responses ===")
    
    # Scenario 1: Empty content
    content = ""
    print("\nScenario 1: Empty content")
    try:
        parsed = json.loads(content)
        print("This should not execute")
    except json.JSONDecodeError as e:
        print(f"✅ Correctly caught JSON error: {str(e)}")
        
    # Scenario 2: Malformed JSON
    content = "{ 'intent': 'set_color', location: 'bedroom' }"
    print("\nScenario 2: Malformed JSON")
    try:
        parsed = json.loads(content)
        print("This should not execute")
    except json.JSONDecodeError as e:
        print(f"✅ Correctly caught JSON error: {str(e)}")
    
    # Scenario 3: Missing closing bracket
    content = '{ "intent": "set_color", "location": "bedroom"'
    print("\nScenario 3: Missing closing bracket")
    try:
        parsed = json.loads(content)
        print("This should not execute")
    except json.JSONDecodeError as e:
        print(f"✅ Correctly caught JSON error: {str(e)}")

if __name__ == "__main__":
    print("Testing OpenAI API Integration")
    print("-" * 50)
    
    # Test actual API with improved error handling
    test_parse_success()
    
    # Test defensive JSON parsing strategies for Render
    test_defensive_json_parsing()
    
    # Test simulated basic error scenarios
    simulate_error_handling()
    
    print("\nTest complete!")