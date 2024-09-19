from logger import logger
import logging
import json
import os
import requests
import config
import graphql

def notify_change_status():
    if config.is_enterprise:
        # Get the issues
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True}
        )
    else:
        # Get the issues
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    # Check if there are issues available
    if not issues:
        logger.info('No issues have been found')
        return

    for projectItem in issues:
        issue = projectItem.get('content')
        if not issue:
            logger.warning(f'Issue object does not contain "content": {projectItem}')
            continue
        
        logger.info(f'Issue object: {json.dumps(issue, indent=2)}')  # Log the full issue object for debugging

        
        issue_id = issue.get('id')
        if issue.get('state') == 'CLOSED':
            continue

        issue_title = issue.get('title', 'Unknown Title')

        # Check the first project item
        project_items = issue.get('projectItems', {}).get('nodes', [])
        if project_items:
            current_status = project_items[0] 
            logger.info(f"current status: {current_status}")
        else:
            logger.warning('No project items found for issue')

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
