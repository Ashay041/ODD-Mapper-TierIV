import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_network_filters():
    print("Testing Network Filters...")

    # 0. Initialize Session (Call /query)
    print("\n0. Initializing Session (POST /query)...")
    payload_query = {
        "input_type": "POINT",
        "input": [36.11454, 137.95489],
        "dist": 500, # Reduced distance for speed
        "default_query": False
    }
    try:
        resp_query = requests.post(f"{BASE_URL}/query", json=payload_query)
        if resp_query.status_code == 200:
            print("Session Initialized.")
        else:
            print(f"Failed to initialize session: {resp_query.status_code} - {resp_query.text}")
            return
    except Exception as e:
        print(f"Exception during initialization: {e}")
        return

    # 0.5 Populate Database (Call /road_features/)
    print("\n0.5 Populating Database (POST /road_features/)...")
    try:
        resp_features = requests.post(f"{BASE_URL}/road_features/")
        if resp_features.status_code == 200:
            print("Database Populated.")
        else:
            print(f"Failed to populate database: {resp_features.status_code} - {resp_features.text}")
            return
    except Exception as e:
        print(f"Exception during population: {e}")
        return

    # 1. Test ALL (No filter)
    print("\n1. Testing odd_type='all'...")
    payload_all = {
        "odd_type": "all"
    }
    try:
        resp_all = requests.post(f"{BASE_URL}/network", json=payload_all)
        if resp_all.status_code == 200:
            data = resp_all.json()
            if isinstance(data, dict):
                coords = data.get('coordinates', [])
                print(f"Coordinates length: {len(coords) if coords else 0}")
            elif isinstance(data, list):
                print(f"Response is a list: {data}")
        else:
            print(f"Error: {resp_all.status_code} - {resp_all.text}")
    except Exception as e:
        print(f"Exception: {e}")

    # 2. Test Live Filter (Motorway)
    print("\n2. Testing odd_type='live' with highway_type=['motorway']...")
    payload_motorway = {
        "odd_type": "live",
        "odd_param": {
            "highway_type": ["motorway"]
        }
    }
    try:
        resp_motorway = requests.post(f"{BASE_URL}/network", json=payload_motorway)
        if resp_motorway.status_code == 200:
            data = resp_motorway.json()
            if isinstance(data, dict):
                coords = data.get('coordinates', [])
                print(f"Coordinates length: {len(coords) if coords else 0}")
            elif isinstance(data, list):
                print(f"Response is a list: {data}")
        elif resp_motorway.status_code == 204:
             print("Response Status: 204 (No Content - Empty Network)")
        else:
            print(f"Error: {resp_motorway.status_code} - {resp_motorway.text}")
    except Exception as e:
        print(f"Exception: {e}")

    # 3. Test Live Filter (Residential)
    print("\n3. Testing odd_type='live' with highway_type=['residential']...")
    payload_residential = {
        "odd_type": "live",
        "odd_param": {
            "highway_type": ["residential"]
        }
    }
    try:
        resp_residential = requests.post(f"{BASE_URL}/network", json=payload_residential)
        if resp_residential.status_code == 200:
            data = resp_residential.json()
            if isinstance(data, dict):
                coords = data.get('coordinates', [])
                print(f"Coordinates length: {len(coords) if coords else 0}")
            elif isinstance(data, list):
                print(f"Response is a list: {data}")
        elif resp_residential.status_code == 204:
             print("Response Status: 204 (No Content - Empty Network)")
        else:
            print(f"Error: {resp_residential.status_code} - {resp_residential.text}")
    except Exception as e:
        print(f"Exception: {e}")
        
    # 4. Test Live Filter (Impossible Condition)
    print("\n4. Testing odd_type='live' with impossible condition (speed_limit=0)...")
    payload_impossible = {
        "odd_type": "live",
        "odd_param": {
            "speed_limit": 0
        }
    }
    try:
        resp_impossible = requests.post(f"{BASE_URL}/network", json=payload_impossible)
        if resp_impossible.status_code == 200:
            data = resp_impossible.json()
            if isinstance(data, dict):
                coords = data.get('coordinates', [])
                print(f"Coordinates length: {len(coords) if coords else 0}")
            elif isinstance(data, list):
                print(f"Response is a list: {data}")
        elif resp_impossible.status_code == 204:
             print("Response Status: 204 (No Content - Empty Network)")
        else:
            print(f"Error: {resp_impossible.status_code} - {resp_impossible.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_network_filters()
