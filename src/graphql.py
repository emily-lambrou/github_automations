from pprint import pprint
import logging
import requests
import config
import json

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


# Update the release field for the issue
def update_issue_release(issue_id, release_option_id, project_id, release_field_id):
    mutation = """
    mutation($issueId: ID!, $releaseOptionId: ID!, $projectId: ID!, $releaseFieldId: ID!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $issueId,
        fieldId: $releaseFieldId,
        value: {id: $releaseOptionId}
      }) {
        projectV2Item {
          id
        }
      }
    }
    """
    variables = {
        "issueId": issue_id,
        "releaseOptionId": release_option_id,
        "projectId": project_id,
        "releaseFieldId": release_field_id
    }

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": mutation, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
        response.raise_for_status()
        data = response.json()

        if 'errors' in data:
            logging.error(f"Error updating release field: {data['errors']}")
            return False

        logging.info(f"Successfully updated issue {issue_id} to the release option.")
        return True

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return False
