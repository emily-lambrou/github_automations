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

    for issue in issues: 
        # Skip the issues if it's closed
        if issue.get('state') == 'CLOSED':
            continue

        # Print the issue object for debugging
        print("Issue object: ", json.dumps(issue, indent=4))

        issue_title = issue.get('title', 'Unknown Title')
        
        # Ensure 'id' is present in issue content
        issue_id = issue_content.get('id')
        if not issue_id:
            logger.warning(f'Issue content does not contain "id": {issue_content}')
            continue

        # Get the project item from issue
        project_items = issue.get('projectItems', {}).get('nodes', [])
        if not project_items:
            logger.warning(f'No project items found for issue {issue_id}')
            continue
        
        # Check the first project item
        project_item = project_items[0]
        if not project_item.get('fieldValueByName'):
            logger.warning(f'Project item does not contain "fieldValueByName": {project_item}')
            continue

        current_status = project_item['fieldValueByName'].get('name')
        if not current_status:
            logger.warning(f'No status found in fieldValueByName for project item: {project_item}')
            continue

        if current_status == 'QA Testing':
            continue # Skip this issue and move to the next since it is already in QA Testing, no need to update
        else:
            has_merged_pr = graphql.get_issue_has_merged_pr(issue_id)
            logger.info(f'This issue has merged PR? : {has_merged_pr}')
            if has_merged_pr:  
                logger.info(f'Proceeding updating the status of {issue_title}, to QA Testing as the issue {issue_title} contains a merged PR.')
        

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
