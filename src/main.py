import re
import graphql
import logger
import test
from datetime import datetime
import logging
import config

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
        logging.info('No issues have been found')
        return

    # Get the project_id, release_field_id 
    project_title = 'Test'
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )

    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None
    
    release_field_name = config.release_field_name
    release_options = graphql.get_all_release_options(project_id, release_field_name)
    
    if not release_options:
        logging.error("Failed to fetch release options.")
        return

    # Define the mapping of date ranges to release names
    date_to_release = {
        ("2024-11-13", "2024-12-06"): "Nov 13 - Dec 06, 2024 (v0.8.9)",
        ("2024-12-09", "2025-01-06"): "Dec 09, 2024 - Jan 06, 2025 (v0.9.0)",
        # Add more ranges and releases as needed
    }
        
    for project_item in issues:
        if project_item.get('state') == 'CLOSED':
            continue

        issue_content = project_item.get('content', {})
        if not issue_content:
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            continue

        # Get the due date value
        due_date = None
        due_date_obj = None
        
        try:
            due_date = project_item.get('fieldValueByName', {}).get('date')
            if due_date:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                logging.info(f"Due date is: {due_date_obj}.")

                # Determine the corresponding release option ID based on the due date
                matching_release_name = None
                for (start_date, end_date), release_name in date_to_release.items():
                    if datetime.strptime(start_date, "%Y-%m-%d").date() <= due_date_obj <= datetime.strptime(end_date, "%Y-%m-%d").date():
                        matching_release_name = release_name
                        break

            if not matching_release_name:
                logging.warning(f"No matching release found for due date {due_date_obj}. Skipping.")
                continue

            release_option_id = release_options.get(matching_release_name)
            if not release_option_id:
                logging.error(f"Release option ID for {matching_release_name} not found. Skipping.")
                continue

                item_found = False
                for item in graphql.get_project_items(project_id):
                    if item.get('content') and item['content'].get('id') == issue_id:
                        item_id = item['id']
                        item_found = True


                        if due_date_obj == '2024-12-26':
                        
                            # Update the issue with the corresponding release option ID
                            updated = graphql.update_issue_release(
                                owner=config.repository_owner,
                                project_title=project_title,
                                project_id=project_id,
                                release_field_id=release_field_name,
                                item_id=item_id,
                                release_option_id='8a45317c'
                            )
                            if updated:
                                logging.info(f"Successfully updated issue {issue_id} to release {matching_release_name}.")
                            else:
                                logging.error(f"Failed to update issue {issue_id}.")
                            break  # Exit the loop once the issue is updated

        except ValueError as e:
            logging.error(f"Error parsing due date for issue {project_item.get('title')}: {e}")
            continue

def main():
    logging.info('Process started...')
    if config.dry_run:
        logging.info('DRY RUN MODE ON!')

    release_based_on_duedate()

if __name__ == "__main__":
    main()
