from pprint import pprint
import logging
import requests
import config

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

def get_repo_issues(owner, repository, after=None, issues=None):
    query = """
    query GetRepoOpenIssues($owner: String!, $repo: String!, $after: String) {
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
        'after': after
    }

    response = requests.post(
        config.api_endpoint,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {config.gh_token}"}
    )

    data = response.json()

    if data.get('errors'):
        print(data.get('errors'))
   
    # Add debug print statement
    pprint(data)

    repository_data = data.get('data', {}).get('repository', {})
    issues_data = repository_data.get('issues', {})
    pageinfo = issues_data.get('pageInfo', {})
    nodes = issues_data.get('nodes', [])

    if issues is None:
        issues = []
    issues = issues + nodes
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
              items(first: 100,after: $after) {{
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
                      assignees(first:20) {{
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

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )
    
        data = response.json()
    
        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return []
          
        owner_data = data.get('data', {}).get(owner_type, {})
        project_data = owner_data.get('projectV2', {})
        items_data = project_data.get('items', {})
        pageinfo = items_data.get('pageInfo', {})
        nodes = items_data.get('nodes', [])
    
        if issues is None:
            issues = []

        if filters:
            filtered_issues = []
            for node in nodes:
                issue_content = node.get('content', {})
                if not issue_content:
                    continue
    
                issue_id = issue_content.get('id')
                if not issue_id:
                    continue
                
                if filters.get('open_only') and node['content'].get('state') != 'OPEN':
                    # logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
                    continue
                
                filtered_issues.append(node)
    
            nodes = filtered_issues
    
        issues = issues + nodes
    
        if pageinfo.get('hasNextPage'):
            return get_project_issues(
                owner=owner,
                owner_type=owner_type,
                project_number=project_number,
                after=pageinfo.get('endCursor'),
                filters=filters,
                issues=issues,
                duedate_field_name=duedate_field_name
            )
    
        return issues
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []

def get_project_items(owner, owner_type, project_number, release_field_name, filters=None, after=None, items=None):
    query = f"""
    query GetProjectItems($owner: String!, $projectNumber: Int!, $release: String!, $after: String) {{
      {owner_type}(login: $owner) {{
        projectV2(number: $projectNumber) {{
          id
          title
          items(first: 100, after: $after) {{
            nodes {{
              id
              fieldValueByName(name: $status) {{
                ... on ProjectV2ItemFieldSingleSelectValue {{
                  id
                  name
                }}
              }}
              content {{
                ... on Issue {{
                  id
                  title
                  state
                  url
                  assignees(first: 10) {{
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
            }}
          }}
        }}
      }}
    }}
    """

    
    variables = {
        'owner': owner,
        'projectNumber': project_number,
        'release': release_field_name,
        'after': after
    }

    try:
        response = requests.post(
            config.api_endpoint,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {config.gh_token}"}
        )

        data = response.json()

        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return []

        owner_data = data.get('data', {}).get(owner_type, {})
        project_data = owner_data.get('projectV2', {})
        items_data = project_data.get('items', {})
        pageinfo = items_data.get('pageInfo', {})
        nodes = items_data.get('nodes', [])

        if items is None:
            items = []

        items += nodes

        if pageinfo.get('hasNextPage'):
            return get_project_items(
                owner=owner,
                owner_type=owner_type,
                project_number=project_number,
                status_field_name=status_field_name,
                after=pageinfo.get('endCursor'),
                items=items
            )

        return items

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []


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
    
    variables = {
        'owner': owner, 
        'projectTitle': project_title
    }

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
                return project['id']
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None

def get_all_release_options(project_id, release_field_name):
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
    variables = {'projectId': project_id}

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

        # Find the field with the matching name
        fields = data['data']['node']['fields']['nodes']
        for field in fields:
            if field.get('name') == release_field_name and field['__typename'] == 'ProjectV2SingleSelectField':
                # Create a dictionary mapping release names to their IDs
                release_options = {
                    option['name']: option['id']
                    for option in field.get('options', [])
                }
                return release_options

        logging.warning(f"Field {release_field_name} not found in project.")
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

def get_release_option_id(project_id, release_field_name):
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
                # Look for the specific options
                for option in field.get('options', []):
                    if option['name'] == "Nov 13 - Dec 06, 2024 (v0.8.9)":
                        option_id = option['id']
                        # logging.info(f"Release Option ID: {option_id}")  # Log the ID for confirmation
                        return option_id
        
        logging.warning(f"Release Nov 13 - Dec 06, 2024 (v0.8.9) not found.")
        return None

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None


def update_release(owner, project_title, project_id, release_field_id, item_id, release_option_id):
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



