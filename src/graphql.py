from pprint import pprint
import logging
import requests
import config

logging.basicConfig(level=logging.DEBUG)  # Ensure logging is set up

def get_repo_issues(owner, repository, after=None, issues=None):
    query = """
    query GetRepoClosedIssues($owner: String!, $repo: String!, $after: String) {
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
            status_field_name=status_field_name
        )

    return issues

def get_project_issues(owner, owner_type, project_number, status_field_name, filters=None, after=None, issues=None):
    query = f"""
    query GetProjectIssues($owner: String!, $projectNumber: Int!, $status: String!, $after: String)  {{
          {owner_type}(login: $owner) {{
            projectV2(number: $projectNumber) {{
              id
              title
              number
              items(first: 100,after: $after) {{
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
                
                if filters.get('open_only') and node['content'].get('state') != 'OPEN':
                    logging.debug(f"Filtering out issue ID {issue_id} with state {issue_content.get('state')}")
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
                status_field_name=status_field_name
            )
    
        return issues
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return []




def get_project_items(owner, owner_type, project_number, status_field_name, filters=None, after=None, items=None):
    query = """
    query GetProjectItems($owner: String!, $projectNumber: Int!, $status: String!, $after: String) {
        repository(owner: $owner, name: $projectNumber) {
            issues(first: 100, after: $after) {
                edges {
                    node {
                        id
                        title
                        state
                        projectItems(first: 10) {
                            nodes {
                                id
                                project {
                                    name
                                }
                                status {
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
            }
        }
    }
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

        # Check for errors in the response
        data = response.json()

        if 'errors' in data:
            logging.error(f"GraphQL query errors: {data['errors']}")
            return []

        repository_data = data.get('data', {}).get('repository', {})
        issues_data = repository_data.get('issues', {})
        pageinfo = issues_data.get('pageInfo', {})
        nodes = issues_data.get('edges', [])

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
