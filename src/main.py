from logger import logger
import config
import graphql


def notify_due_date_changes():
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            duedate_field_name=config.duedate_field_name,
            filters={'open_only': True}
        )
    else:
        # Get the issues
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            duedate_field_name=config.duedate_field_name
        )

    # Check if there are issues available
    if not issues:
        logger.info('No issues have been found')
        return

    for projectItem in issues:
        # Safely extract 'content' from projectItem
        issue = projectItem.get('content')
        if not issue:
            logger.error(f"Missing 'content' in project item: {projectItem}")
            continue

        # Get the list of assignees
        assignees = issue.get('assignees', {}).get('nodes', [])
        
        # Get the due date value
        due_date = None
        due_date_obj = None
        try:
            due_date = projectItem.get('fieldValueByName', {}).get('date')
            if due_date:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
        except (AttributeError, ValueError) as e:
            continue  # Skip this issue and move to the next

        issue_title = issue.get('title', 'Unknown Title')
        issue_id = issue.get('id', 'Unknown ID')

        if not due_date_obj:
            logger.info(f'No due date found for issue {issue_title}')
            continue
        
def print_release_options():
    """Fetch and print release field options."""
    # Fetch the project ID using its title
    project_title = 'Test'
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner,
        project_title=project_title
    )
    
    if not project_id:
        logger.error(f"Project {project_title} not found.")
        return
    
    # Fetch the release field options
    release_options = graphql.get_release_field_options(project_id)
    if release_options:
        logger.info("Release Options (Name -> ID):")
        for name, option_id in release_options.items():
            logger.info(f"{name} -> {option_id}")
    else:
        logger.error("Failed to fetch release options.")


def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    # Print the release options
    print_release_options()

if __name__ == "__main__":
    main()
