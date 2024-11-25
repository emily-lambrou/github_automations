from logger import logger
import config
import graphql

def get_release_fields():
    logger.info('Fetching release fields...')
    
    release_options = graphql.get_release_field_options()
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

    get_release_fields()

if __name__ == "__main__":
    main()
