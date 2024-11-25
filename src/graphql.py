from pprint import pprint
import logging
import requests
import config

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

# Fetch Release Field Options
def get_release_field_options(project_id):
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
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
    
    variables = {'projectId': project_id}

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

        fields = data['data']['node']['fields']['nodes']
        for field in fields:
            if field['name'] == "Release":  # Match your field name
                logging.info(f"Found 'Releases' field with options.")
                return {option['name']: option['id'] for option in field['options']}

        logging.warning("Releases field not found in the project.")
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
