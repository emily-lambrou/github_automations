from pprint import pprint
import logging
import requests
import config

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up


# Define the query to fetch release field options
QUERY = """
query {
  node(id: "YOUR_PROJECT_ID") {
    ... on ProjectV2 {
      fields(first: 50) {
        nodes {
          ... on ProjectV2SingleSelectField {
            name
            options {
              id
              name
            }
          }
        }
      }
    }
  }
}
"""

# Fetch field options
def get_release_field_options():
    response = requests.post(API_URL, json={"query": query}, headers=headers)
    if response.status_code == 200:
        fields = response.json()["data"]["node"]["fields"]["nodes"]
        for field in fields:
            if field["name"] == "Releases":  # Match your field name
                return {option["name"]: option["id"] for option in field["options"]}
    else:
        print(f"Error fetching field options: {response.status_code}, {response.text}")
        return None

# Example usage
release_options = get_release_field_options()
if release_options:
    print("Release Options (Name -> ID):", release_options)
