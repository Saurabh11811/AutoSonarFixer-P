#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSonarFixer Orchestrator (Fully Normalized Version)
"""

import os
import sys
import logging

# Dynamically compute project root
project_root = os.path.dirname(os.path.abspath(__file__))

# Unified sys.path injection
sys.path.append(os.path.join(project_root, "utils"))
sys.path.append(os.path.join(project_root, "phase1_clone_and_detect"))
sys.path.append(os.path.join(project_root, "phase3_build_and_compile"))
sys.path.append(os.path.join(project_root, "phase4_sonar_scan"))
# Later we'll add phase5_autofix path here

# Import modules
from config_manager import ConfigManager
import clone_repo
import detect_tech_stack
import build_project
import sonar_scanner

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    config = ConfigManager()

    for repo in config.get_enabled_repos():
        repo_url = repo['repo_url']
        clone_path = repo['local_clone_path']
        api_token = repo.get('api_token', '')

        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        full_repo_path = os.path.join(clone_path, repo_name)

        logging.info(f"\n===== Processing Repo: {repo_url} =====")

        # PHASE 1 — Clone
        try:
            if not os.path.exists(clone_path):
                os.makedirs(clone_path)
            clone_repo.clone_repo(repo_url, clone_path)
        except Exception as e:
            logging.error(f"Skipping repo due to clone failure: {e}")
            continue

        # PHASE 2 — Tech stack detection
        try:
            final_stack = detect_tech_stack.detect_tech_stack(
                repo_url, full_repo_path, api_token
            )
            logging.info(f"Detected Tech Stack: {final_stack}")
            config.update_repo_entry(repo_url, 'detected_tech_stack', final_stack)
        except Exception as e:
            logging.error(f"Skipping repo due to detection failure: {e}")
            continue

        # PHASE 3 — Build
        try:
            build_project.run_build_for_repo(repo)
        except Exception as e:
            logging.error(f"Build failed for {repo_url}: {e}")
            continue  # optional: allow sonar scan even if build failed

        # PHASE 4 — Initial Sonar Scan
        try:
            sonar_scanner.run_full_sonar_pipeline(
                full_repo_path, repo_name, config.config
            )
        except Exception as e:
            logging.error(f"Sonar phase failed for {repo_url}: {e}")
            continue
        
    
    # After all repos processed:
    sys.path.append(os.path.join(project_root, "phase4_sonar_scan"))
    import sonar_summary_reporter
    sonar_summary_reporter.run_summary()
    logging.info("✅ Full Orchestration Run Completed.")
