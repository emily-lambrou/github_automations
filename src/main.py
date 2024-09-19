from logger import logger
import logging
import json
import os
import requests
import config
import graphql

def notify_change_status(project_id,status_field_id):
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

    # Loop through issues
    for issue in issues:
        # Skip the issues if it's closed
        if issue.get('state') == 'CLOSED':
            continue
        
        # Print the issue object for debugging
        print("Issue object: ", json.dumps(issue, indent=4))

        # Ensure 'content' is present
        issue_content = issue.get('content', {})
        if not issue_content:
            logger.warning(f'Issue object does not contain "content": {issue}')
            continue

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

        item_id = graphql.get_item_id_by_issue_id(
            project_id=project_id,
            issue_id=issue_id
        )
        
        if not item_id:
            logging.error(f"Item id not found in project {project_title}.")
            return None

        status_name = "QA Testing"
            
        current_status = project_item['fieldValueByName'].get('name')
        
        # Check if the current status is "QA Testing"
        if current_status == 'QA Testing':
            continue # Skip this issue and move to the next since it is already in QA Testing, no need to update
        else:
            
            if not config.dry_run: # if True then enable the functionality to update the status
                
                # Check if the PR is merged from the issue timelines
                has_merged_pr = graphql.get_issue_has_merged_pr(issue_id)
                if has_merged_pr:  
                    logger.info(f'Proceeding updating the status of {issue_title}, to QA Testing as the issue {issue_title} contains a merged PR.')
                    graphql.update_issue_status_to_qa_testing(
                        owner=config.repository_owner,
                        project_title=project_title,
                        item_id=item_id,
                        status_name=status_name
                    )
                
def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    # -----------------------------------------------------------------------------
    # General variables to run only once to get the project_id and status_field_id
    # -----------------------------------------------------------------------------

    project_title = 'George Test'
    
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )
    
    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None
    
    status_field_id = graphql.get_status_field_id(
        project_id=project_id,
        status_field_name=config.status_field_name
    )
    
    if not status_field_id:
        logging.error(f"Status field not found in project {project_title}.")
        return None
    
    # -----------------------------------------------------------------------------

    notify_change_status(project_id,status_field_id)

if __name__ == "__main__":
    main()
