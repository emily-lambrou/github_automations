from logger import logger
import logging
import json
import requests
import config
import graphql


def get_release_fields():
    project_title = 'Test'

    release_options = graphql.get_release_field_options()
    if release_options:
    print("Release Options (Name -> ID):", release_options)


def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    get_release_fields()

if __name__ == "__main__":
    main()
