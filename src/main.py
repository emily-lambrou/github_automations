from logger import logger
import config
import graphql
from datetime import datetime
import re

# Patterns or criteria to exclude certain releases
EXCLUDED_PATTERNS = [
    "Unicaf Release",  # Example: exclude releases with "Unicaf Release" in the name
]

# Regex pattern for validating release name format (e.g., includes date range)
RELEASE_DATE_PATTERN = r"\b\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}\b"

def should_exclude_release(release_name):
    """
    Determines if a release should be excluded based on patterns or criteria.
    """
    for pattern in EXCLUDED_PATTERNS:
        if pattern in release_name:
            return True
    return False

def is_valid_release_format(release_name):
    """
    Validates the format of a release name to check for expected date ranges.
    """
    return re.search(RELEASE_DATE_PATTERN, release_name) is not None

def find_matching_release(release_options, due_date):
    """
    Find the correct release based on the due date.
    :param release_options: Dictionary of release options with date ranges
    :param due_date: The due date to match
    :return: Matching release option or None
    """
    for release_name, release_data in release_options.items():
        # Skip excluded or invalid releases
        if should_exclude_release(release_name):
            logger.info(f"Excluding release: {release_name}")
            continue
        if not is_valid_release_format(release_name):
            logger.warning(f"Skipping release due to invalid format: {release_name}")
            continue

        if release_data['start_date'] <= due_date <= release_data['end_date']:
            return release_data
    return None

def release_based_on_duedate():
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            duedate_field_name=config.duedate_field_name,
            filters={'open_only': True}
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            duedate_field_name=config.duedate_field_name
        )

    if not issues:
        logger.info('No issues have been found')
        return

    #-------------------------------------------
    # Get the project_id, release_field_id 
    #-------------------------------------------

    project_title = 'Test'
    
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )

    if not project_id:
        logger.error(f"Project {project_title} not found.")
        return None
    
    release_field_id = graphql.get_release_field_id(
        project_id=project_id,
        release_field_name=config.release_field_name
    )

    if not release_field_id:
        logger.error(f"Release field not found in project {project_title}")
        return None

    #-------------------------------------------------------------------------
    
    release_options = graphql.get_release_field_options(project_id)
    if not release_options:
        logger.error("Failed to fetch release options.")
        return

    for project_item in issues:

        # Skip the closed issues
        if project_item.get('state') == 'CLOSED':
            continue
            
        # Ensure the issue contains content
        issue_content = project_item.get('content', {})
        if not issue_content:
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            continue

        due_date = project_item.get('fieldValueByName', {}).get(config.duedate_field_name)
        if not due_date:
            logger.info(f"No due date for issue {project_item.get('title')}. Skipping.")
            continue

        # Parse and compare the due date
        try:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            release_to_update = find_matching_release(release_options, due_date_obj)

            if release_to_update:
                logger.info(f"Due date for issue {project_item.get('title')} is {due_date_obj}. Changing release...")

                # Find the item id for the issue
                item_found = False
                for item in graphql.get_project_items(project_id):  # Assume this function fetches project items
                    if item.get('content') and item['content'].get('id') == issue_id:
                        item_id = item['id']
                        
                        item_found = True
                        
                        logger.info(f"Proceeding to update the release")

                        # Update the release field for the issue
                        updated = graphql.update_issue_release(
                            owner=config.repository_owner,
                            project_title=project_title,
                            project_id=project_id,
                            release_field_id=release_field_id,
                            item_id=item_id,
                            release_option_id=release_to_update['id']
                        )
                        if updated:
                            logger.info(f"Successfully updated issue {issue_id} to the release option.")
                        else:
                            logger.error(f"Failed to update issue {issue_id}.")
                        break  # Break out of the loop once updated
                    
                if not item_found:
                    logger.warning(f'No matching item found for issue ID: {issue_id}.')
                    continue  # Skip the issue as it cannot be updated
                    
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse due date for issue {project_item.get('title')}. Error: {e}")
            continue


def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    # Notify about due date changes and release updates
    release_based_on_duedate()

if __name__ == "__main__":
    main()
