import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_root():
    print("Testing Root Route (GET /)...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

def test_query_place():
    print("Testing Query Endpoint (POST /query) - Place...")
    payload = {
        "input_type": "PLACE",
        "input": "Shiojiri, Nagano Prefecture, Japan",
        "default_query": False,
        "default_settings": True,
        "default_conflict_classifier": True,
        "odd_all": True
    }
    try:
        response = requests.post(f"{BASE_URL}/query", json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

def test_query_point():
    print("Testing Query Endpoint (POST /query) - Point...")
    payload = {
        "input_type": "POINT",
        "input": [36.11454, 137.95489],
        "dist": 500,
        "default_query": False
    }
    try:
        response = requests.post(f"{BASE_URL}/query", json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print("Error Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    test_root()
    # test_query_place() # Commented out to avoid large data download on first try
    test_query_point()
