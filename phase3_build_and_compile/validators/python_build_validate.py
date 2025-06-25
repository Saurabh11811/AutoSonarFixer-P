import os
import logging
import subprocess
import glob
import venv
import shutil

# Setup logger (module-level)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def syntax_check(repo_path, python_path='python3'):
    logging.info("Starting syntax check...")
    py_files = glob.glob(os.path.join(repo_path, '**', '*.py'), recursive=True)

    if not py_files:
        logging.warning("No Python files found.")
        return

    failed_files = []
    for file in py_files:
        result = subprocess.run(
            [python_path, "-m", "py_compile", file],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logging.error(f"File: {file} ... ERROR")
            logging.error(result.stderr)
            failed_files.append(file)
        else:
            logging.info(f"File: {file} ... OK")

    if failed_files:
        raise Exception("Syntax check failed on some files.")

def create_virtualenv(repo_path):
    venv_path = os.path.join(repo_path, 'venv_autosonar')
    if os.path.exists(venv_path):
        shutil.rmtree(venv_path)

    logging.info("Creating virtualenv...")
    venv.EnvBuilder(with_pip=True).create(venv_path)
    return venv_path

def install_dependencies(venv_path, repo_path):
    requirements_file = os.path.join(repo_path, 'requirements.txt')
    if not os.path.exists(requirements_file):
        logging.warning("requirements.txt not found. Skipping dependencies.")
        return

    pip_path = os.path.join(venv_path, 'bin', 'pip')  # Mac/Linux

    logging.info("Installing dependencies...")
    process = subprocess.Popen(
        [pip_path, "install", "-r", requirements_file],
        cwd=repo_path
    )
    process.communicate()

    if process.returncode != 0:
        raise Exception("Dependency installation failed.")

def cleanup_virtualenv(venv_path):
    if os.path.exists(venv_path):
        shutil.rmtree(venv_path)
        logging.info("Virtualenv cleaned up.")

def run_build(repo_path):
    try:
        syntax_check(repo_path)
        venv_path = create_virtualenv(repo_path)
        install_dependencies(venv_path, repo_path)
        cleanup_virtualenv(venv_path)
        logging.info("✅ Python build successfully completed.")
    except Exception as e:
        logging.error(f"❌ Build failed: {e}")
        raise
