import os
import sys
import logging

# Import ConfigManager
sys.path.append("../utils")
from config_manager import ConfigManager

import sys

# Dynamically compute project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append validators folder correctly
validators_path = os.path.join(project_root, "phase3_build_and_compile", "validators")
sys.path.append(validators_path)

import python_build_validate


# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def run_build_for_repo(repo):
    repo_url = repo['repo_url']
    clone_path = repo['local_clone_path']
    tech_stack = repo.get('detected_tech_stack', 'unknown')

    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    full_repo_path = os.path.join(clone_path, repo_name)

    logging.info(f"Running build for: {repo_url} | Stack: {tech_stack}")

    if tech_stack == 'python':
        python_build_validate.run_build(full_repo_path)
    elif tech_stack == 'java-maven':
        logging.warning("Java Maven build not yet implemented.")
    elif tech_stack == 'java-gradle':
        logging.warning("Java Gradle build not yet implemented.")
    else:
        logging.error(f"Unsupported tech stack: {tech_stack}")


#for testing only
if __name__ == "__main__":
    config = ConfigManager()

    for repo in config.get_enabled_repos():
        repo_url = repo['repo_url']
        clone_path = repo['local_clone_path']
        tech_stack = repo.get('detected_tech_stack', 'unknown')

        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        full_repo_path = os.path.join(clone_path, repo_name)

        logging.info(f"Starting build for: {repo_url} | Tech stack: {tech_stack}")

        try:
            if tech_stack == 'python':
                python_build_validate.run_build(full_repo_path)
            elif tech_stack == 'java-maven':
                logging.warning("Java Maven validator not implemented.")
            elif tech_stack == 'java-gradle':
                logging.warning("Java Gradle validator not implemented.")
            else:
                logging.error(f"Unsupported tech stack: {tech_stack}")
        except Exception as e:
            logging.error(f"Build failed for {repo_url}: {e}")
