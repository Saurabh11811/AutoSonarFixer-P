import os
import sys
import git
import logging

# Import new config manager
sys.path.append("../utils")
from config_manager import ConfigManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def clone_repo(repo_url, clone_path):
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    dest_path = os.path.join(clone_path, repo_name)

    if os.path.exists(dest_path):
        logging.warning(f"Directory {dest_path} already exists. Skipping clone.")
        return dest_path

    try:
        logging.info(f"Cloning repository: {repo_url}")
        git.Repo.clone_from(repo_url, dest_path)
        logging.info(f"Repository cloned successfully at: {dest_path}")
        return dest_path
    except git.exc.GitCommandError as e:
        logging.error(f"Git error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)



# should only be used for testing as standalone, else use master script
if __name__ == "__main__":
    config = ConfigManager()
    for repo in config.get_enabled_repos():
        repo_url = repo['repo_url']
        clone_path = repo['local_clone_path']

        if not os.path.exists(clone_path):
            try:
                os.makedirs(clone_path)
                logging.info(f"Created directory: {clone_path}")
            except Exception as e:
                logging.error(f"Failed to create directory {clone_path}: {e}")
                sys.exit(1)

        clone_repo(repo_url, clone_path)
