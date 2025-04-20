# Jarvis-Beta

A lightweight FastAPI backend that receives natural language instructions (via LLM), parses them into structured actions, and controls smart home devices — starting with Philips Hue and Broadlink (via IFTTT).

## Overview

Jarvis-Beta acts as a smart bridge between OpenAI's LLM output and real-world device actions.

### Current Supported Actions:
- `set_color`: Controls Hue lights using color and brightness (using Hue API v2)
- `trigger_scene`: Triggers IFTTT Webhooks for Broadlink or other ecosystem devices

## API Endpoints

### 1. Control Endpoint

**POST /control**

Directly executes smart home actions with structured JSON input.

#### Example JSON Input

```json
{
  "intent": "set_color",
  "location": "bedroom",
  "hue": 53000,
  "sat": 180,
  "bri": 120
}
```

### 2. Parse Endpoint

**POST /parse**

Converts natural language requests into structured actions using OpenAI's o4-mini model.

#### Example Request

```json
{
  "text": "Make the bedroom lights soft pink and dim"
}
```

#### Example Response

```json
{
  "intent": "set_color",
  "location": "bedroom",
  "hue": 52000,
  "sat": 180,
  "bri": 100
}
```

## Setup

1. Create a `.env` file with the following variables:
   - `HUE_BRIDGE_IP`: IP address of your Philips Hue Bridge
   - `HUE_USERNAME`: Your Hue application key (for Hue API v2)
   - `IFTTT_KEY`: Your IFTTT webhook key
   - `OPENAI_API_KEY`: Your OpenAI API key

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the server:
   ```
   uvicorn main:app --reload
   ```

## Technical Notes

- The Philips Hue integration uses the Hue API v2 (CLIP API)
- HSB color values are automatically converted to CIE xy color space for Hue API v2 compatibility
- SSL certificate verification is disabled for local Hue Bridge communication




curl -s -X POST https://jarvis-beta.onrender.com/execute -H "Content-Type: application/json" -d '{"text": "Turn on the AC"}'