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

    #----------------------------------------------------------------------------------------
    # Get the project_id and status_field_id: 
    #----------------------------------------------------------------------------------------

    project_title = 'George Test'
    
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )

    logger.info(f'Printing the project_id: {project_id}')

    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None
    
    status_field_id = graphql.get_status_field_id(
        project_id=project_id,
        status_field_name=config.status_field_name
    )

    logger.info(f"Printing the status_field_id: {status_field_id}")

    if not status_field_id:
        logging.error(f"Status field not found in project {project_title}")
        return None

    #----------------------------------------------------------------------------------------


    
    items = graphql.get_project_items(
        owner=config.repository_owner, 
        owner_type=config.repository_owner_type,
        project_number=config.project_number,
        status_field_name=config.status_field_name
    )

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
            logger.info(f'Skipping issue as it is already in QA Testing.')
            continue
        else:
            has_merged_pr = graphql.get_issue_has_merged_pr(issue_id)
            logger.info(f'This issue has merged PR? : {has_merged_pr}')
            if has_merged_pr:  
                logger.info(f'Proceeding to update the status to QA Testing as it contains a merged PR.')

                # Find the item id for the issue
                item_id = None
                for item in items:
                    if item.get('content') and item['content'].get('id') == issue_id:
                        item_id = item['id']
                        break
                logger.info(f'Item id for issue {issue_id}: {item_id}')

                if not item_id:
                    logger.error(f'Item id not fount for issue {issue_id} in project {project_title}')
                    continue #  Skip the issue as it cannot be updated

                # Proceed to update the status
                
                status_option_id = "MDM1OlByb2plY3RWMkl0ZW1GaWVsZFNpbmdsZVNlbGVjdFZhbHVlOTY2MTE=" 

                update_result = graphql.update_issue_status_to_qa_testing(
                    owner=config.repository_owner,
                    project_title=project_title,
                    project_id=project_id,
                    status_field_id=status_field_id,
                    item_id=item_id,
                    status_option_id=status_option_id
                )

                if update_result:
                    logger.info(f'Successfully updated issue {issue_id} to QA Testing.')
                else:
                    logger.error(f'Failed to update issue {issue_id}.')
        
               

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
