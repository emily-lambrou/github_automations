from pprint import pprint
import logging
import requests
import config
import json
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

def get_repo_issues(owner, repository, duedate_field_name, after=None, issues=None):
    query = """
    query GetRepoIssues($owner: String!, $repo: String!, $duedate: String!, $after: String) {
          repository(owner: $owner, name: $repo) {
            issues(first: 100, after: $after, states: [OPEN]) {
              nodes {
                id
                title
                number
                url
                assignees(first:100) {
                  nodes {
                    name
                    email
                    login
                  }
                }
                projectItems(first: 10) {
                  nodes {
                    project {
                      number
                      title
                    }
                    fieldValueByName(name: $duedate) {
                      ... on ProjectV2ItemFieldDateValue {
                        id
                        date
                      }
                    }
                  }
                }
              }
              pageInfo {
                endCursor
                hasNextPage
                hasPreviousPage
              }
              totalCount
            }
          }
        }
    """

    variables = {
        'owner': owner,
        'repo': repository,
        'duedate': duedate_field_name,
        'after': after
    }

    response = requests.post(
        config.api_endpoint,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )

    if response.json().get('errors'):
        print(response.json().get('errors'))

    pageinfo = response.json().get('data').get('repository').get('issues').get('pageInfo')
    if issues is None:
        issues = []
    issues = issues + response.json().get('data').get('repository').get('issues').get('nodes')
    if pageinfo.get('hasNextPage'):
        return get_repo_issues(
            owner=owner,
            repository=repository,
            after=pageinfo.get('endCursor'),
            issues=issues,
            duedate_field_name=duedate_field_name
        )

    return issues


def get_project_issues(owner, owner_type, project_number, duedate_field_name, filters=None, after=None, issues=None):
    query = f"""
    query GetProjectIssues($owner: String!, $projectNumber: Int!, $duedate: String!, $after: String)  {{
          {owner_type}(login: $owner) {{
            projectV2(number: $projectNumber) {{
              id
              title
              number
              items(first: 100, after: $after) {{
                nodes {{
                  id
                  fieldValueByName(name: $duedate) {{
                    ... on ProjectV2ItemFieldDateValue {{
                      id
                      date
                    }}
                  }}
                  content {{
                    ... on Issue {{
                      id
                      title
                      number
                      state
                      url
                      assignees(first: 20) {{
                        nodes {{
                          name
                          email
                          login
                        }}
                      }}
                    }}
                  }}
                }}
                pageInfo {{
                  endCursor
                  hasNextPage
                  hasPreviousPage
                }}
                totalCount
              }}
            }}
          }}
        }}
    """

    variables = {
        'owner': owner,
        'projectNumber': project_number,
        'duedate': duedate_field_name,
        'after': after
    }

    response = requests.post(
        config.api_endpoint,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )

    if response.json().get('errors'):
        logging.error(response.json().get('errors'))
        return []

    page_info = response.json().get('data').get(owner_type).get('projectV2').get('items').get('pageInfo')
    nodes = response.json().get('data').get(owner_type).get('projectV2').get('items').get('nodes')

    if filters:
        filtered_issues = []
        for node in nodes:
            if filters.get('open_only') and node['content'].get('state') != 'OPEN':
                continue
            filtered_issues.append(node)
        nodes = filtered_issues

    issues = issues or []
    issues += nodes

    if page_info.get('hasNextPage'):
        return get_project_issues(
            owner=owner,
            owner_type=owner_type,
            project_number=project_number,
            after=page_info.get('endCursor'),
            filters=filters,
            issues=issues,
            duedate_field_name=duedate_field_name
        )

    return issues

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

# Fetch and map release options by date range
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

        fields = data['data']['node']['fields']['nodes']
        release_options = {}

        # Iterate through the fields to find the Releases field
        for field in fields:
            field_name = field.get('name')
            if field_name == "Release":
                for option in field.get('options', []):
                    release_name = option['name']
                    release_id = option['id']
                    
                    # Try to parse the date range from the release name, e.g., "Nov 13 - Dec 06, 2024"
                    date_range = extract_date_range_from_release_name(release_name)
                    if date_range:
                        release_options[release_name] = {
                            'id': release_id,
                            'start_date': date_range[0],
                            'end_date': date_range[1]
                        }

        if not release_options:
            logging.warning("No release options found in the project.")
        return release_options

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

# Extract date range from the release name (e.g., "Nov 13 - Dec 06, 2024 (v0.8.9)")
def extract_date_range_from_release_name(release_name):
    # Assuming the date range is in the format "Nov 13 - Dec 06, 2024"
    try:
        date_part = release_name.split(" (")[0]  # Remove version part
        start_date_str, end_date_str = date_part.split(" - ")
        
        # Parse the date strings
        start_date = datetime.strptime(start_date_str + ", 2024", "%b %d, %Y").date()
        end_date = datetime.strptime(end_date_str + ", 2024", "%b %d, %Y").date()
        
        return (start_date, end_date)
    except Exception as e:
        logging.error(f"Failed to extract date range from release name: {release_name}. Error: {e}")
        return None

def get_release_field_id(project_id, release_field_name):
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 100) {
            nodes {
              __typename
              ... on ProjectV2SingleSelectField {
                id
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
    variables = {
        'projectId': project_id
    }

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        
        data = response.json()

        # Check for errors in the response
        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return None
        
        # Ensure 'data' is in the response and is valid
        if 'data' not in data or 'node' not in data['data'] or 'fields' not in data['data']['node']:
            logging.error(f"Unexpected response structure: {data}")
            return None
        
        # Log the response for debugging
        logging.debug(f"GraphQL response: {data}")

        # Get fields from the response
        fields = data['data']['node']['fields']['nodes']
        for field in fields:
            if field.get('name') == release_field_name and field['__typename'] == 'ProjectV2SingleSelectField':
                return field['id']
        
        logging.warning(f"Release field '{release_field_name}' not found.")
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

def get_item_id_by_issue_id(project_id, issue_id):
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue {
                  id
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "projectId": project_id
    }
    
    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        
        data = response.json()
        project_items = data.get('data', {}).get('node', {}).get('items', {}).get('nodes', [])
        
        for item in project_items:
            if item.get('content') and item['content'].get('id') == issue_id:
                return item['id']
        
        return None
        
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

# Update the release field for the issue
def update_issue_release(owner, project_title, project_id, release_field_id, item_id, release_option_id):
    mutation = """
    mutation UpdateIssueRelease($projectId: ID!, $itemId: ID!, $releaseFieldId: ID!, $releaseOptionId: String!) {
        updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $releaseFieldId,
            value: {
                singleSelectOptionId: $releaseOptionId  
            }
        }) {
            projectV2Item {
                id
            }
        }
    }
    """
    
    variables = {
        'projectId': project_id,   
        'itemId': item_id,         
        'releaseFieldId': release_field_id, 
        'releaseOptionId': release_option_id  
    }

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": mutation, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        
        data = response.json()
        if 'errors' in data:
            logging.error(f"GraphQL mutation errors: {data['errors']}")
            return None
        return data.get('data')

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
