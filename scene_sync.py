import os
import requests

HUE_BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
HUE_USERNAME = os.getenv("HUE_USERNAME")

def fetch_scenes():
    url = f"https://{HUE_BRIDGE_IP}/clip/v2/resource/scene"
    headers = {
        "hue-application-key": HUE_USERNAME,
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()
    scenes = response.json().get("data", [])
    scene_dict = {}
    location_to_group = {}
    for scene in scenes:
        name = scene.get("metadata", {}).get("name", "")
        scene_id = scene.get("id")
        group = scene.get("group", {})
        group_id = group.get("rid")
        group_type = group.get("rtype")
        # Use the original scene name as key (case preserved) for LLM to trigger by name
        scene_dict[name] = {
            "id": scene_id,
            "group_id": group_id,
            "group_type": group_type
        }
        if group_type == "room" and name.lower() not in location_to_group:
            location_to_group[name.lower()] = group_id
    return scene_dict, location_to_group

if __name__ == "__main__":
    scenes, groups = fetch_scenes()
    print("SCENE_NAME_TO_INFO = {")
    for name, info in scenes.items():
        print(f'    "{name}": {info},')
    print("}")
    print()
    print("LOCATION_TO_GROUP_ID = {")
    for loc, gid in groups.items():
        print(f'    "{loc}": "{gid}",')
    print("}")