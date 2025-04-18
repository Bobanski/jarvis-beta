from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv

# Test command for simulating smart control flow
test_command = "Turn on the AC"

# System prompt context for lighting moods and scenes
SYSTEM_PROMPT_CONTEXT = """
Lighting context guidelines:
- TV: dimmer lights, warm color temperature
- Napping: dim and warm, colors like orange, dark orange, or red
- Sleepy: dim and warm, similar to napping, promotes relaxation
- Concentrating/Studying: brighter, cooler white or soft blue tones
- Chill/Relaxing: soft, warm colors with moderate brightness
- Energizing/Vibrant: bright and saturated colors
- Default: warm light unless specified otherwise
- Avoid cold white lights unless explicitly requested for focus or study
- Adjust brightness and hue to match the mood description

LLM Parsing Rules:
If the user wants to control the TV (turn on/off/power TV) via IFTTT, set intent: "trigger_ifttt", device: "tv", and command: "on" or "off".
If the user wants to control the air conditioning (turn on/off AC), set intent: "trigger_ifttt", device: "ac", and command: "on" or "off".
If the user wants to open the curtains, set intent: "trigger_ifttt", device: "curtains", and command: "open".
If the user wants to control the LG TV directly, set intent: "lg_tv_control" and include "command" field with the action.
If the user wants to change room lighting, fallback to existing set_color or trigger_scene logic.
"""

load_dotenv()

app = FastAPI()

# Load from .env
HUE_BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
HUE_USERNAME = os.getenv("HUE_USERNAME")  # Hue API token
IFTTT_KEY = os.getenv("IFTTT_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Dictionary mapping locations to their group IDs
LOCATION_TO_GROUP_ID = {
    "bedroom": "fc8b3e68-4a00-409d-a279-6ec19c6e74e6",
    "living_room": "d342a23c-26db-417c-a345-b47d67f184ad"
}

# Dictionary mapping scene names to their UUIDs
SCENE_NAME_TO_ID = {
    "stefan": "cb2c4125-aa86-48ce-b6d1-08781127f91c",
    "rio": "e483a90d-8546-4964-a6f7-69401aa9b167",
    "arctic aurora": "efc4b0a7-620e-4749-9a56-fe03afdb9ab1",
    "ruby glow": "f5e98e36-6271-4051-8d13-f9214dc705ea",
    "stef night": "f7a95b99-990e-4624-be51-7c71c16e7588",
    "miami": "97be9237-8cee-484a-ab6b-406e03ab37fa",
    "rose sake": "5d26e305-6098-4b44-ad37-509565a338e8",
    "bright": "6a076389-e48d-4735-859f-07141c26f859",
    "soho": "777b5186-b0f7-42ce-ada9-b495a0d38595",
    "savanna sunset": "8d68731c-2b94-42d5-8f64-fbb4c9381cab",
    "amber bloom": "9115b70d-e286-4ccb-b524-3cfc2de965b4",
    "fireplace": "92ed5558-0303-4cd2-b9d6-c9f09abdb76c",
    "movie mode": "97be9237-8cee-484a-ab6b-406e03ab37fa",
    "blood moon": "9e07edec-1918-4206-a1f1-aa61b266de99",
    "dani calm": "a57127c9-6dd9-4080-88b8-a564ac27272a",
    "read": "ad8d406a-c0d1-47ae-bd6d-644651634fee",
    "relax": "b11ed74d-8dd9-4cb1-bddf-b99e3f238774",
    "chill": "bd48ced6-cace-4f7f-8518-f454c4e9a0ca",
    "sunset": "c471d2b9-2a97-4efb-81b9-43cfaa4bfc65",
    "dimmed": "cb2c4125-aa86-48ce-b6d1-08781127f91c",
    "concussion": "d1250619-218f-4c95-aa2a-5e9be1c555bd",
    "peggy": "db577267-64ef-41e7-823b-1e55f59012cc",
    "glowing grins": "027bcc8d-8f2c-4781-8bd7-26c0e310a625",
    "whiskey": "112acc16-c1a1-4613-8a3f-acda3b47a76f",
    "sunrise": "11d449cc-be37-4d3d-91e3-05b479b64db0",
    "nightlight": "134cc20a-ea87-4424-b292-ed698084754f",
    "neon": "15e7a902-2fd1-45ac-a3f3-96f3a42cb728",
    "the vibes": "2f1dfb78-f4a4-47b5-8de6-f7d9ff8e9310",
    "trick or treat": "385dfb6a-2736-4ee2-ba4a-d5319fdd8a04",
    "concentrate": "3edb3490-1cd7-43c2-ae4f-1ba254a55505",
    "tangeriney": "50e132cf-b70d-48ce-a13c-ecbe7e57eede",
    "sesh": "15b7bf23-b5a3-44c2-9a6b-86f001eefcbd"
}


@app.post("/control")
async def control(request: Request):
    try:
        data = await request.json()
        intent = data.get("intent")

        # Inject system prompt context for lighting moods and scenes
        if "mood_description" in data:
            data["system_prompt_context"] = SYSTEM_PROMPT_CONTEXT

        if intent == "set_color":
            return await handle_set_color(data)
        elif intent == "trigger_scene":
            return handle_trigger_scene(data)
        elif intent == "trigger_ifttt":
            return await handle_ifttt_trigger(data)
        elif intent == "lg_tv_control":
            return await handle_lg_tv_control(data)
        else:
            return JSONResponse(content={"error": "Unknown intent"}, status_code=400)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

def hsb_to_xy(hue, saturation, brightness):
    """
    Convert Philips Hue HSB values to CIE xy color space.
    
    Args:
        hue: 0-65535 (Hue API range)
        saturation: 0-254 (Hue API range)
        brightness: 0-254 (Hue API range)
        
    Returns:
        tuple: (x, y) coordinates in CIE color space
    """
    # Normalize values to 0-1 range
    h = float(hue) / 65535.0
    s = float(saturation) / 254.0
    b = float(brightness) / 254.0
    
    # Convert to RGB
    if s == 0:
        r = g = b = b
    else:
        h = h * 6.0

async def handle_ifttt_trigger(data):
    """
    Handle the trigger_ifttt intent for TV, AC, and curtains control via IFTTT webhook.
    Expects data to contain "device" and optional "command" ("on" or "off" for TV/AC, "open" for curtains).
    """
    device = data.get("device")
    command = data.get("command", "on").lower()

    if device not in ("tv", "ac", "curtains"):
        return JSONResponse(content={"error": "Unsupported device for trigger_ifttt"}, status_code=400)

    if device in ("tv", "ac"):
        if command not in ("on", "off"):
            return JSONResponse(content={"error": "Invalid command for device control, must be 'on' or 'off'"}, status_code=400)
    elif device == "curtains":
        if command != "open":
            return JSONResponse(content={"error": "Invalid command for curtains control, must be 'open'"}, status_code=400)

    if device == "tv":
        ifttt_url = "https://maker.ifttt.com/trigger/TV_power/json/with/key/kCQ-0Z6Eqoas4hL5lXU3T2sv3YDoS4iL6GQ0wXx5X2r"
    elif device == "ac":
        ifttt_url = "https://maker.ifttt.com/trigger/ac_power/json/with/key/kCQ-0Z6Eqoas4hL5lXU3T2sv3YDoS4iL6GQ0wXx5X2r"
    else:  # curtains
        ifttt_url = "https://maker.ifttt.com/trigger/Open_curtains/json/with/key/kCQ-0Z6Eqoas4hL5lXU3T2sv3YDoS4iL6GQ0wXx5X2r"
        command = "open"  # force command to open for curtains

    payload = {"value1": command}

    try:
        response = requests.post(ifttt_url, json=payload, timeout=5)
        response.raise_for_status()
        return {"status": "success", "message": f"{device.upper()} command '{command}' sent to IFTTT."}
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"Failed to send IFTTT webhook: {str(e)}"}, status_code=500)

async def handle_lg_tv_control(data):
    """
    Handle the lg_tv_control intent for direct LG TV control via webOS API.
    Expects data to contain "command" field with the action to perform.
    This is a stub implementation; actual communication with LG TV requires network access and webOS protocol.
    """
    command = data.get("command")
    if not command:
        return JSONResponse(content={"error": "Missing command for LG TV control"}, status_code=400)

    # TODO: Implement actual LG webOS TV control logic here.
    # This may involve sending requests to the TV's webOS service endpoints,
    # possibly via websockets or REST API if available.
    # For now, just simulate success.

    return {"status": "success", "message": f"LG TV command '{command}' received (stub implementation)."}

    i = int(h)
    f = h - i
    p = b * (1.0 - s)
    q = b * (1.0 - s * f)
    t = b * (1.0 - s * (1.0 - f))
    
    if i == 0:
        r, g, b = b, t, p
    elif i == 1:
        r, g, b = q, b, p
    elif i == 2:
        r, g, b = p, b, t
    elif i == 3:
        r, g, b = p, q, b
    elif i == 4:
        r, g, b = t, p, b
    else:
        r, g, b = b, p, q

    # Apply inverse gamma correction (sRGB to linear RGB)
    r = pow((r + 0.055) / 1.055, 2.4) if r > 0.04045 else r / 12.92
    g = pow((g + 0.055) / 1.055, 2.4) if g > 0.04045 else g / 12.92
    b = pow((b + 0.055) / 1.055, 2.4) if b > 0.04045 else b / 12.92

    # Convert linear RGB to XYZ using standard matrix for sRGB D65 illuminant
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # Calculate xy values
    try:
        x = X / (X + Y + Z)
        y = Y / (X + Y + Z)
    except ZeroDivisionError:
        x, y = 0.0, 0.0
    
    return round(x, 4), round(y, 4)

async def handle_set_color(data):
    location = data.get("location")
    hue = data.get("hue")
    sat = data.get("sat")
    bri = data.get("bri")
    
    # If any parameter is missing, try to parse descriptive color/brightness strings
    if location is None or hue is None or sat is None or bri is None:
        color_desc = data.get("color_description")
        brightness_desc = data.get("brightness_description")
        mood_desc = data.get("mood_description")
        # Accept location even if missing color_description if hue/sat/bri are present
        if not location or (not color_desc and (hue is None or sat is None or bri is None)):
            return JSONResponse(
                content={"error": "Missing required parameters: location and color_description or hue/sat/bri"},
                status_code=400
            )
        # Map descriptive strings to numerical values if hue/sat/bri missing
        if hue is None or sat is None or bri is None:
            hue, sat = map_color_description_to_hue_sat(color_desc, mood_desc)
            bri = map_brightness_description_to_bri(brightness_desc)
            # Lock saturation to 100% regardless of input or mapping
            sat = 254
    else:
        # Normalize hue value - support both degrees (0-360) and Hue API scale (0-65535)
        hue = int(hue)  # Ensure hue is an integer
        if hue <= 360:
            # Convert from degrees to Hue API scale
            hue = int((hue / 360.0) * 65535)
        # Lock saturation to 100% regardless of input
        sat = 254
    
    # Convert HSB to xy color space
    x, y = hsb_to_xy(hue, sat, bri)
    
    # Convert brightness from 0-254 to 0-100 range for API v2
    brightness_percent = min(100.0, max(0.0, (float(bri) / 254.0) * 100.0))
    
    # Get group ID from location
    group_id = get_group_id_from_location(location)
    if not group_id:
        return JSONResponse(content={"error": "Invalid location"}, status_code=400)
    
    url = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/grouped_light/{group_id}"
    headers = {
        "hue-application-key": HUE_USERNAME,
        "Content-Type": "application/json"
    }
    
    payload = {
        "on": {"on": True},
        "dimming": {"brightness": brightness_percent},
        "color": {"xy": {"x": x, "y": y}}
    }
    
    try:
        res = requests.put(url, json=payload, headers=headers, verify=False)
        res.raise_for_status()  # Raise exception for 4XX/5XX responses
        return JSONResponse(content={"status": "Hue command sent", "response": res.json()})
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            content={"error": f"Failed to communicate with Hue Bridge: {str(e)}"},
            status_code=500
        )

# Helper functions to map descriptive strings to numerical values

# Define base colors (Hue scale 0-65535, Sat 0-254)
BASE_COLORS = {
    "red": (0, 254),
    "warm red": (2000, 230), # Shifted slightly towards orange
    "orange": (5461, 254),
    "yellow": (10922, 254),
    "lime": (16384, 254),
    "green": (21845, 254),
    "spring green": (27306, 254),
    "cyan": (32768, 254),
    "sky blue": (38000, 200),
    "blue": (43690, 254),
    "purple": (49151, 254),
    "magenta": (52000, 254),
    "pink": (54613, 254),
    "light pink": (56000, 180),
    "white": (0, 0), # Saturation 0 means white regardless of hue
    "warm white": (7000, 100), # Example: Use low sat, adjust hue towards orange/yellow
    "cool white": (38000, 50) # Example: Use low sat, adjust hue towards blue
}

def map_color_description_to_hue_sat(color_desc, mood_desc=None):
    if not color_desc:
        return BASE_COLORS["white"] # Default to white if no color specified

    color_desc = color_desc.lower()
    mood_desc = mood_desc.lower() if mood_desc else None

    # --- Handle specific mood/color combinations first ---
    if mood_desc in ["calming", "relaxing", "sleepy", "chill", "nap", "napping"]:
        if "red" in color_desc:
            # Calm/Relaxing Red: Warmer hue, lower saturation
            return (3000, 180) # Shift hue towards orange, reduce saturation
        elif "orange" in color_desc:
            # Warm orange for napping
            return (5461, 200)
        elif "blue" in color_desc:
            # Calm/Relaxing Blue: Shift hue slightly towards cyan, lower saturation
            return (40000, 160)
        elif "green" in color_desc:
             # Calm/Relaxing Green: Less vibrant green, lower saturation
            return (24000, 170)
        else:
            # Default warm orange for nap/chill if no color specified
            return (5461, 200)

    # --- Fallback to base color lookup and generic mood adjustment ---
    hue, sat = BASE_COLORS.get(color_desc, BASE_COLORS["warm white"])

    # Generic mood adjustments (if no specific combination was matched)
    if mood_desc:
        if mood_desc in ["calming", "relaxing", "sleepy", "soft", "chill", "nap", "napping"]:
            sat = 254  # Lock saturation to 100%
        elif mood_desc in ["energizing", "vibrant", "bright"]:
            sat = 254  # Lock saturation to 100%
        # Add more generic mood adjustments if needed

    return hue, sat

def map_brightness_description_to_bri(brightness_desc):
    # Brightness map (0-254 scale)
    brightness_map = {
        "off": 0, # Technically handled by 'on:false', but good to have
        "minimum": 1,
        "very dim": 25,
        "dim": 60, # Adjusted from 50
        "sleepy": 40, # Added
        "soft": 100, # Added
        "normal": 150,
        "bright": 220, # Adjusted from 254
        "full": 254,
        "max": 254,
        "maximum": 254
    }
    if not brightness_desc:
        return brightness_map["normal"] # Default brightness

    return brightness_map.get(brightness_desc.lower(), brightness_map["normal"])


def handle_trigger_scene(data):
    scene_name = data.get("scene_name")
    if not scene_name:
        return JSONResponse(content={"error": "Missing scene_name"}, status_code=400)
    
    # Normalize scene name to lowercase
    scene_name = scene_name.lower()
    
    # Get scene ID from the dictionary
    scene_id = SCENE_NAME_TO_ID.get(scene_name)
    
    # If scene not found directly, try fuzzy matching
    if not scene_id and SCENE_NAME_TO_ID:
        scene_id = fuzzy_match_scene(scene_name, SCENE_NAME_TO_ID)
    
    if not scene_id:
        return JSONResponse(
            content={"error": f"Unknown scene: {scene_name}"},
            status_code=400
        )
    
    # Get location/group from data or use default
    location = data.get("location", "living_room")
    group_id = get_group_id_from_location(location)
    
    if not group_id:
        return JSONResponse(content={"error": "Invalid location"}, status_code=400)
    
    # Call Hue v2 API to recall the scene via group action endpoint
    url = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/scene/{scene_id}" # Revert to scene endpoint
    headers = {
        "hue-application-key": HUE_USERNAME,
        "Content-Type": "application/json"
    }
    
    # Try payload for recalling scene via its own endpoint
    payload = {
        "recall": {
            "action": "active"
        }
    }
    
    try:
        res = requests.put(
            url,
            json=payload,
            headers=headers,
            verify=False
        )
        res.raise_for_status()
        return JSONResponse(content={"status": "Scene activated", "response": res.json()})
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            content={"error": f"Failed to activate scene: {str(e)}"},
            status_code=500
        )

def fuzzy_match_scene(query, scene_dict):
    """
    Find the closest matching scene name using simple fuzzy matching.
    
    Args:
        query: The scene name to search for
        scene_dict: Dictionary of scene names to IDs
        
    Returns:
        The ID of the best matching scene, or None if no good match
    """
    if not query or not scene_dict:
        return None
    
    # Simple matching algorithm based on substring and character overlap
    best_score = 0
    best_match = None
    
    for scene_name, scene_id in scene_dict.items():
        # Check for substring match (weighted heavily)
        if query in scene_name or scene_name in query:
            score = 3 * min(len(query), len(scene_name))
        else:
            # Count matching characters
            score = sum(1 for c in query if c in scene_name)
        
        # Adjust score based on length difference
        score = score / (1 + abs(len(query) - len(scene_name)))
        
        if score > best_score:
            best_score = score
            best_match = scene_id
    
    # Only return a match if the score is reasonable
    return best_match if best_score > 1 else None



def get_group_id_from_location(location):
    return LOCATION_TO_GROUP_ID.get(location.lower())



from openai import OpenAI
import json

@app.post("/parse")
async def parse(request: Request):
    import logging
    try:
        data = await request.json()
        logging.info(f"Received /parse request data: {data}")
        text = data.get("text")
        if not text:
            return JSONResponse(content={"error": "Missing 'text' field"}, status_code=400)

        # Get valid scene names and locations
        scene_name_options = ", ".join([f'"{name}"' for name in SCENE_NAME_TO_ID.keys()])
        location_options = ", ".join([f'"{loc}"' for loc in LOCATION_TO_GROUP_ID.keys()])
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        system_prompt = (
            "You are a smart home controller. "
            "Interpret the user's natural language request and extract structured information. "
            "Return the output as a JSON object. "
            "Determine if the request matches a known lighting scene OR describes a color. "
            "If it matches a scene name, set intent to 'trigger_scene' "
            "and include 'scene_name' and 'location' fields. "
            f"scene_name must be one of: {scene_name_options}. "
            f"location must be one of: {location_options}. "
            "If it describes a color (e.g., 'warm orange', 'deep blue'), set intent to 'set_color' and include "
            "'location', 'hue' (0-360), 'sat' (0-254), and 'bri' (0-254) fields. "
            "Always normalize scene names to lowercase."
            + "\n\n" + SYSTEM_PROMPT_CONTEXT
        )
        user_prompt = f"Request: {text}"

        # Configure retry logic for better reliability in cloud environments
        max_retries = 2
        retry_count = 0
        last_exception = None
        
        while retry_count <= max_retries:
            try:
                # Use response_format to ensure we get valid JSON
                # This is more reliable than parsing from content directly
                response = client.chat.completions.create(
                    model="o4-mini-2025-04-16",  # Pinned to specific snapshot for consistency
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},  # Explicitly request JSON output
                    temperature=1,  # Lower temperature for more predictable responses
                    timeout=15  # Explicit timeout for cloud environments
                )
                
                # Log full raw response for debugging
                logging.info(f"Full OpenAI response: {response}")
                
                # Check if we have a valid response with content
                if not response.choices or len(response.choices) == 0:
                    error_msg = "OpenAI API returned empty choices"
                    logging.error(error_msg)
                    return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
                
                # Check if message exists and has content
                message = response.choices[0].message
                if not hasattr(message, 'content') or message.content is None:
                    error_msg = "OpenAI API response missing content field"
                    logging.error(error_msg)
                    return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
                
                content = message.content.strip()
                logging.info(f"OpenAI response content: {content}")
                
                if not content:
                    error_msg = "OpenAI API returned empty content"
                    logging.error(error_msg)
                    return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
                
                # Validate JSON response - this should be more reliable now with response_format
                try:
                    parsed = json.loads(content)
                    # Success - return the parsed data
                    return JSONResponse(content=parsed)
                except json.JSONDecodeError as json_err:
                    # Still failed to parse JSON despite response_format
                    error_msg = f"Failed to parse JSON from OpenAI response: {str(json_err)}"
                    logging.error(error_msg)
                    
                    # Final attempt - do a defensive JSON string fix
                    try:
                        # Try to fix common JSON issues
                        clean_content = content.replace("'", '"')  # Replace single quotes with double quotes
                        clean_content = clean_content.strip()
                        
                        # Ensure it starts and ends with braces
                        if not clean_content.startswith('{'):
                            clean_content = '{' + clean_content
                        if not clean_content.endswith('}'):
                            clean_content = clean_content + '}'
                            
                        fixed_parsed = json.loads(clean_content)
                        logging.warning(f"JSON was fixed with defensive parsing: {clean_content}")
                        return JSONResponse(content=fixed_parsed)
                    except json.JSONDecodeError:
                        # If we're on the last retry, return the error
                        if retry_count == max_retries:
                            return JSONResponse(
                                content={
                                    "error": error_msg,
                                    "raw_content": content
                                },
                                status_code=500
                            )
                        # Otherwise, increment retry counter and try again
                        retry_count += 1
                        continue
                    
            except Exception as e:
                last_exception = e
                # If we're on the last retry, raise the exception
                if retry_count == max_retries:
                    raise
                # Otherwise, increment retry counter and try again
                retry_count += 1
                logging.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}")
                continue
                
        # We should never get here, but just in case
        return JSONResponse(
            content={"error": f"Failed after {max_retries} retries. Last error: {str(last_exception)}"},
            status_code=500
        )
    except Exception as e:
        logging.error(f"Exception in /parse endpoint: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


async def run_smart_control_from_text(text):
    """
    Simulate the full smart control flow using natural language input.
    
    Args:
        text: Natural language command (e.g., "Make the bedroom a warm orange")
        
    Returns:
        Result of the control operation
    """
    print(f"Processing command: '{text}'")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    


    # Get valid scene names and locations
    scene_name_options = ", ".join([f'"{name}"' for name in SCENE_NAME_TO_ID.keys()])
    location_options = ", ".join([f'"{loc}"' for loc in LOCATION_TO_GROUP_ID.keys()])
    
    # Define prompts
    system_prompt = (
        "You are a smart home controller. "
        "Interpret the user's natural language request and return ONLY a valid JSON object. "
        "Determine if the request matches a known lighting scene OR describes a color. "
        "If it matches a scene name, set intent to 'trigger_scene' "
        "and include 'scene_name' and 'location' fields. "
        f"scene_name must be one of: {scene_name_options}. "
        f"location must be one of: {location_options}. "
        "If it describes a color (e.g., 'warm orange', 'deep blue'), set intent to 'set_color' and include "
        "'location', 'hue' (0-360), 'sat' (0-254), and 'bri' (0-254) fields. "
        "Always normalize scene names to lowercase. "
        "Do not include any explanation or extra text, only return valid JSON.\n\n"
        + SYSTEM_PROMPT_CONTEXT
    )
    user_prompt = f"Request: {text}"
    
    # Call OpenAI API
    try:
        # Use response_format to ensure we get valid JSON
        response = client.chat.completions.create(
            model="o4-mini-2025-04-16",  # Pinned to specific snapshot for consistency
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},  # Explicitly request JSON output
            temperature=1,  # Lower temperature for more predictable responses
            timeout=15  # Explicit timeout for cloud environments
        )
        
        # Check if we have a valid response with content
        if not response.choices or len(response.choices) == 0:
            error_msg = "OpenAI API returned empty choices"
            print(f"Error: {error_msg}")
            return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
            
        # Check if message exists and has content
        message = response.choices[0].message
        if not hasattr(message, 'content') or message.content is None:
            error_msg = "OpenAI API response missing content field"
            print(f"Error: {error_msg}")
            return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
            
        content = message.content.strip()
        
        if not content:
            error_msg = "OpenAI API returned empty content"
            print(f"Error: {error_msg}")
            return JSONResponse(content={"error": error_msg, "raw_response": str(response)}, status_code=500)
        
        # Extract and parse response
        try:
            parsed_data = json.loads(content)
            print("Parsed command data:")
            print(json.dumps(parsed_data, indent=2))
            
            # Handle the intent
            intent = parsed_data.get("intent")
            if intent == "set_color":
                result = await handle_set_color(parsed_data)
                print("Result of set_color operation:")
                print(result.body.decode())
                return result
            elif intent == "trigger_scene":
                result = handle_trigger_scene(parsed_data)
                print("Result of trigger_scene operation:")
                print(result.body.decode())
                return result
            elif intent == "trigger_ifttt":
                result = await handle_ifttt_trigger(parsed_data)
                print("Result of trigger_ifttt operation:")
                print(result)
                return result
            elif intent == "lg_tv_control":
                result = await handle_lg_tv_control(parsed_data)
                print("Result of lg_tv_control operation:")
                print(result)
                return result
            else:
                print(f"Unknown intent: {intent}")
                return JSONResponse(content={"error": "Unknown intent"}, status_code=400)
        except json.JSONDecodeError as json_err:
            error_msg = f"Failed to parse JSON from OpenAI response: {str(json_err)}"
            print(f"Error: {error_msg}")
            print(f"Raw response: {content}")
            return JSONResponse(
                content={
                    "error": error_msg,
                    "raw_content": content
                },
                status_code=500
            )
    except Exception as e:
        print(f"Error processing command: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/execute")
async def execute_command(request: Request):
    """
    Combined endpoint that parses natural language and executes the command.
    This endpoint first parses the text to structured data, then calls the appropriate
    handler to execute the command.
    """
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return JSONResponse(content={"error": "Missing 'text' field"}, status_code=400)
        
        # First parse the text
        parse_response = await parse(Request(scope={"type": "http"}, receive=request.receive))
        
        # Check if parsing was successful
        if isinstance(parse_response, JSONResponse):
            if parse_response.status_code != 200:
                return parse_response
            
            # Extract the parsed data
            parsed_data = parse_response.body
            if isinstance(parsed_data, bytes):
                parsed_data = json.loads(parsed_data.decode())
            
            # Now execute the command based on the intent
            intent = parsed_data.get("intent")
            if intent == "set_color":
                return await handle_set_color(parsed_data)
            elif intent == "trigger_scene":
                return handle_trigger_scene(parsed_data)
            elif intent == "trigger_ifttt":
                return await handle_ifttt_trigger(parsed_data)
            elif intent == "lg_tv_control":
                return await handle_lg_tv_control(parsed_data)
            else:
                return JSONResponse(content={"error": "Unknown intent", "parsed_data": parsed_data}, status_code=400)
        else:
            return JSONResponse(content={"error": "Failed to parse command"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": f"Error executing command: {str(e)}"}, status_code=500)

if __name__ == "__main__":
    import asyncio
    
    # Run the test command
    print("Running smart control simulation...")
    asyncio.run(run_smart_control_from_text(test_command))

