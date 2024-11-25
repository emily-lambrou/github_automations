from pprint import pprint
import logging
import requests
import config
import json

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

# Fetch Project ID by Title
def get_project_id_by_title(owner, project_title):
    query = """
    query($owner: String!, $projectTitle: String!) {
      organization(login: $owner) {
        projectsV2(first: 10, query: $projectTitle) {
          nodes {
            id
            title
          }
        }
      }
    }
    """
    
    variables = {'owner': owner, 'projectTitle': project_title}

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        data = response.json()

        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return None

        projects = data['data']['organization']['projectsV2']['nodes']
        for project in projects:
            if project['title'] == project_title:
                logging.info(f"Found project '{project_title}' with ID: {project['id']}")
                return project['id']
        logging.warning(f"Project '{project_title}' not found.")
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

def get_release_field_options(project_id):
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              __typename
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
    variables = {'projectId': project_id}

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        response.raise_for_status()
        data = response.json()

        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return None

        # Debugging: Log the raw fields structure
        fields = data['data']['node']['fields']['nodes']
        logging.debug(f"Fetched fields: {json.dumps(fields, indent=2)}")

        # Iterate through the fields to find the Releases field
        for field in fields:
            field_name = field.get('name')  
            if field_name == "Release":  
                return {option['name']: option['id'] for option in field.get('options', [])}

        logging.warning("Releases field not found in the project.")
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

