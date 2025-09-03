import requests
import json

BASE_URL='http://localhost:5000'

def test_embed_single():
    url = f"{BASE_URL}/embed"
    payload = {"text": "Hello, world!"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "embedding" in data
    assert isinstance(data["embedding"], list)
    assert all(isinstance(x, float) for x in data["embedding"])

def test_single_insertion():
    url = f"{BASE_URL}/insert"
    payload = {
        "text": "Sample listing text",
        "user_id": "123",
        "user_name": "Test User"
    }
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], int)

def test_batch_insertion():
    url = f"{BASE_URL}/batchInsertion"
    with open("UGA.json", "r") as f:
        payload = json.load(f)
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "inserted_ids" in data
    assert isinstance(data["inserted_ids"], list)
    assert all(isinstance(x, int) for x in data["inserted_ids"])
    assert len(data["inserted_ids"]) == len(payload)
def test_search():
    url = f"{BASE_URL}/search"
    payload = {
        "query": "Looking for a 2 bedroom apartment under $1500",
        "max_price": 1500,
        "min_beds": 2,
        "top_k": 3
    }
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    #print(data)
    # Pretty-print the JSON data with an indentation of 4 spaces
    pretty_json_string = json.dumps(data, indent=4)
    print(pretty_json_string)
if __name__ == "__main__":  
    #test_single_insertion()
    #test_batch_insertion()
    #test_embed_single()
    test_search()
