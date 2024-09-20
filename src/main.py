from logger import logger
import logging
import json
import requests
import config
import graphql

def notify_change_status():
    # Fetch issues based on whether it's an enterprise or not
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
        # Skip the issues if they are closed
        if issue.get('state') == 'CLOSED':
            continue

        # Ensure the issue contains content
        issue_content = issue.get('content', {})
        if not issue_content:
            logger.warning(f'Issue does not contain content: {issue}')
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            logger.warning('Issue does not have an ID')
            continue

        # Debugging output for the issue
        logger.info("Issue object: %s", json.dumps(issue, indent=4))

        # Safely get the fieldValueByName and current status
        field_value = issue.get('fieldValueByName')
        current_status = field_value.get('name') if field_value else None
        logger.info(f'The current status of this issue is: {current_status}')
        
        issue_title = issue.get('title')

        if current_status == 'QA Testing':
            logger.info(f'Skipping {issue_title} as it is already in QA Testing.')
            continue
        else:
            logger.info(f'Current status is NOT QA Testing for {issue_title}.')
            has_merged_pr = graphql.get_issue_has_merged_pr(issue_id)
            logger.info(f'This issue has merged PR? : {has_merged_pr}')
            if has_merged_pr:  
                logger.info(f'Proceeding to update the status of {issue_title} to QA Testing as it contains a merged PR.')

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
