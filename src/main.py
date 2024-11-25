from logger import logger
import config
import graphql

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
