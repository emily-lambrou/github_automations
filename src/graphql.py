from pprint import pprint
import logging
import requests
import config

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

def get_repo_issues(owner, repository, status_field_name, after=None, issues=None):
    query = """
    query GetRepoIssues($owner: String!, $repo: String!, $status: String!, $after: String) {
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
                    fieldValueByName(name: $status) {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        id
                        name
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
        'status': status_field_name,
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
            status_field_name=status_field_name
        )

    return issues

def get_project_issues(owner, owner_type, project_number, status_field_name, filters=None, after=None, issues=None):
    query = f"""
    query GetProjectIssues($owner: String!, $projectNumber: Int!, $status: String!, $after: String) {{
        {owner_type}(login: $owner) {{
            projectV2(number: $projectNumber) {{
                id
                title
                number
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
        'status': status_field_name,
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

                # Safely get the fieldValueByName and current status
                field_value = node.get('fieldValueByName')
                current_status = field_value.get('name') if field_value else None
       
                # Apply the 'open_only' filter if specified
                if filters.get('open_only') and issue_content.get('state') != 'OPEN':
                    logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
                    continue
               
            # Update nodes with the filtered list
            nodes = filtered_issues
    
        # Append filtered nodes to issues
        issues = issues + nodes
    
        if pageinfo.get('hasNextPage'):
            return get_project_issues(
                owner=owner,
                owner_type=owner_type,
                project_number=project_number,
                after=pageinfo.get('endCursor'),
                filters=filters,
                issues=issues,
                status_field_name=status_field_name
            )
    
        return issues
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

def get_status_field_id(project_id, status_field_name):
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
            if field.get('name') == status_field_name and field['__typename'] == 'ProjectV2SingleSelectField':
                return field['id']
        
        logging.warning(f"Status field '{status_field_name}' not found.")
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
        project_items = data['data']['node']['items']['nodes']
        
        # Find the project-specific `item_id` that matches the `issue_id`
        for item in project_items:
            if item['content'] and item['content']['id'] == issue_id:
                return item['id']
        return None

        
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
        
def get_issue_has_merged_pr(issue_id):
    query = """
    query GetIssueTimeline($issueId: ID!, $afterCursor: String) {
        node(id: $issueId) {
            ... on Issue {
                timelineItems(first: 100, after: $afterCursor) {
                    nodes {
                        __typename
                        ... on CrossReferencedEvent {
                            source {
                                ... on PullRequest {
                                    id
                                    number
                                    mergedAt
                                    url
                                }
                            }
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
    }
    """
    
    variables = {
        'issueId': issue_id,
        'afterCursor': None
    }

    try:
        while True:
            response = requests.post(
                config.api_endpoint,
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": f"Bearer {config.gh_token}",
                    "Accept": "application/vnd.github.v4+json"
                }
            )

            data = response.json()

            if 'errors' in data:
                logging.error(f"GraphQL query errors: {data['errors']}")
                break

            timeline_data = data.get('data', {}).get('node', {}).get('timelineItems', {})
            timeline_items = timeline_data.get('nodes', [])

            # Check each timeline item for a merged pull request
            for item in timeline_items:
                if item['__typename'] == 'CrossReferencedEvent':
                    pr = item.get('source', {})
                    if pr.get('mergedAt'):
                        return True  # A merged pull request was found

            pageinfo = timeline_data.get('pageInfo', {})
            if not pageinfo.get('hasNextPage'):
                break

            # Set the cursor for the next page
            variables['afterCursor'] = pageinfo.get('endCursor')

        # No merged pull request found in the timeline
        return False

    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return False

def update_issue_status_to_qa_testing(owner, project_title, item_id, status_name):
    project_id = get_project_id_by_title(owner, project_title)
    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None

    status_field_id = get_status_field_id(project_id, config.status_field_name)
    if not status_field_id:
        logging.error(f"Status field not found in project {project_title}.")
        return None

    item_id = get_item_id_by_issue_id(project_id, issue_id)  
    if not item_id:
        logging.error(f"Item id not found in project {project_title}.")
        return None

    mutation = """
    mutation UpdateIssueStatus($projectId: ID!, $itemId: ID!, $statusFieldId: ID!, $statusName: String!) {
        updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $statusFieldId,
            value: { singleSelectOptionId: $statusName }
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
        'statusFieldId': status_field_id,
        'statusName': status_name
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
        logging.info(f"Updated issue status to '{status_name}' for item ID: {item_id}")
        return data.get('data')
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
