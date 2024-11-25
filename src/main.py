from logger import logger
import logging
import json
import requests
import config
import graphql


def get_release_fields():
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

    
    project_title = 'Test'
    

def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    get_release_fields()

if __name__ == "__main__":
    main()
