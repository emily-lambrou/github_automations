from logger import logger
import logging
import json
import os
import requests
import config
import graphql

def notify_change_status():
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True}
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    if not issues:
        logger.info('No issues have been found')
        return

    for projectItem in issues:
        issue = projectItem.get('content')
        if not issue:
            logger.warning(f'Issue object does not contain "content": {projectItem}')
            continue
        
        logger.info(f'Issue object: {json.dumps(issue, indent=2)}')  # Debugging info

        issue_id = issue.get('id')
        if issue.get('state') == 'CLOSED':
            continue

        issue_title = issue.get('title', 'Unknown Title')

        # Call get_project_items if needed
        project_items = graphql.get_project_items(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name
        )
        
        logger.info(f"Project items: {json.dumps(project_items, indent=2)}")

        # Check if projectItems exists and is a list
        project_items = issue.get('projectItems', {})
        
        if isinstance(project_items, dict):
            nodes = project_items.get('nodes', [])
            if nodes:
                current_status = nodes[0] 
                logger.info(f"current status: {current_status}")
            else:
                logger.warning(f'No project items nodes found for issue ID {issue_id}')
        else:
            logger.warning(f'Project items field is not a dict or is missing for issue ID {issue_id}')


def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
