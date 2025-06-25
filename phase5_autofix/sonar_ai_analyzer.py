import os
import sys
import json
import datetime
import logging
from pymongo import MongoClient
import requests
import ollama
import pandas as pd
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ==== CONFIG LOADER ====
sys.path.append("../utils")
from config_manager import ConfigManager

config_mgr = ConfigManager()
config = config_mgr.config

# ==== MONGODB CONNECTION ====

def connect_to_mongodb(db_config):
    if 'username' in db_config and db_config['username']:
        client = MongoClient(
            host=db_config['host'], port=db_config['port'],
            username=db_config['username'], password=db_config['password'])
    else:
        client = MongoClient(host=db_config['host'], port=db_config['port'])
    db = client[db_config['db_name']]
    return db[db_config['collection']]

# ==== LATEST NORMALIZED FILE ====

def get_latest_normalized_file(normalized_path):
    files = [f for f in os.listdir(normalized_path) if f.endswith("_normalized_issues.json")]
    if not files:
        logging.error(f"❌ No normalized issues file found in {normalized_path}")
        return None
    files.sort(reverse=True)
    return os.path.join(normalized_path, files[0])

# ==== LOAD ISSUES ====

def load_issues_by_file(normalized_json_path):
    with open(normalized_json_path, 'r') as f:
        issues = json.load(f)
    issues_by_file = defaultdict(list)
    for issue in issues:
        if issue.get('type') != 'SECURITY_HOTSPOT':
            issues_by_file[issue['file']].append(issue)
    return issues_by_file

# ==== PROMPT BUILDER ====

def build_llm_prompt(file_content, issues, file_name):
    issue_descriptions = "\n".join([
        f"- Rule: {i['rule']}, Severity: {i['severity']}, Line: {i['line']}, Message: {i['message']}"
        for i in issues
    ])

    prompt_parts = [
        "You are an expert software engineer tasked with automatically fixing ALL code quality issues related to the rules listed below.",
        "",
        f"You are tasked to fix ALL code quality issues detected by SonarQube for the following file: `{file_name}`.",
        "",
        "⚠️ IMPORTANT:",
        "- The file can be any type (Python, YAML, Dockerfile, shell script, config, etc).",
        "- Always apply rule fixes according to the file's format, language and context.",
        "",
        f"SonarQube reported {len(issues)} issue(s):",
        issue_descriptions,
        "",
        "🛠️ **Your Tasks:**",
        "- Carefully scan the **entire file**, not only the specific lines mentioned above.",
        "- Apply comprehensive fixes for all occurrences of the same rule types across any part of the file, even if not explicitly listed above.",
        "- Apply each rule correction across the entire file globally wherever relevant.",
        "- Apply consistent fixes for all similar rule patterns, across all functions, classes, and nested blocks.",
        "- Do not introduce unrelated refactoring or stylistic changes unrelated to these rules.",
        "- Preserve file's valid syntax, code logic, functionality, docstrings, comments, and overall code structure.",
        "- Add any necessary imports if required for your fixes.",
        "- Avoid excessive code deletions unless strictly necessary to fix rule violations.",
        "",
        "**Strict Guidelines:**",
        "- Do not invent unrelated improvements or rewrite unrelated code.",
        "- Do not remove valid comments, docstrings, metadata, or logic not related to these issues.",
        "- Only apply changes necessary to fix the listed issues and closely related violations.",
        "- Add any missing imports or declarations required to apply the fixes.",
        "- Avoid introducing unrelated refactoring or over-corrections not tied to the listed rules.",
        "- If something needs to be restructured to comply with rule (like cognitive complexity reductions), do so while preserving functionality.",
        "",
        "**IMPORTANT OUTPUT FORMAT:**",
        "- Your output must start with: ```python",
        "- Your output must end with: ```",
        "- Do NOT include any explanation or commentary.",
        "",
        "Here is the full file content you must fix:",
        "```",
        file_content,
        "```",
        "",
        "Please provide ONLY the fully corrected file content now:"
    ]
    

    return "\n".join(prompt_parts)


# ==== CODE EXTRACTION ====

def extract_python_code(llm_output):
    if llm_output is None:
        return None
    inside = False
    code_lines = []
    for line in llm_output.splitlines():
        if not inside and line.strip().startswith("```python"):
            inside = True
            continue
        if inside:
            if line.strip() == "```":
                break
            code_lines.append(line)
    return "\n".join(code_lines).strip() if code_lines else None

# ==== BACKEND HANDLERS ====

def run_local_backend(prompt, config):
    model_name = config['autofix']['model']
    logging.info(f"🧠 Calling LOCAL LLM: {model_name}")
    try:
        response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
        return response['message']['content'], {"model": model_name, "source": "local"}
    except Exception as e:
        logging.error(f"❌ Local LLM call failed: {e}")
        return None, {"model": model_name, "source": "local"}



import time
import openai

def run_azure_backend(prompt, config):
    logging.info("🧠 Calling Azure OpenAI backend via SDK...")

    api_key = config['azure']['key']
    endpoint = config['azure']['endpoint']
    deployment = config['azure']['deployment']
    api_version = config['azure']['version']
    temperature = config['autofix']['temperature']

    # Azure OpenAI SDK style initialization
    client = openai.AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version
    )

    max_retries = 1
    retry_wait = 10  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a software fixer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                timeout=600  # seconds (timeout for entire request)
            )

            # Parse response
            reply = response.choices[0].message.content
            return reply, {"model": deployment, "source": "azure"}

        except openai.RateLimitError:
            logging.warning(f"⚠️ Azure Rate Limit hit (429). Attempt {attempt}/{max_retries}. Retrying after {retry_wait} sec...")
            time.sleep(retry_wait)

        except openai.Timeout:
            logging.warning(f"⚠️ Azure Timeout occurred. Attempt {attempt}/{max_retries}. Retrying after {retry_wait} sec...")
            time.sleep(retry_wait)

        except openai.APIError as e:
            logging.error(f"❌ Azure API Error: {e}")
            return None, {"model": deployment, "source": "azure"}

        except Exception as e:
            logging.error(f"❌ Unexpected error calling Azure OpenAI: {e}")
            return None, {"model": deployment, "source": "azure"}

    logging.error("❌ Maximum retries exhausted for Azure backend.")
    return None, {"model": deployment, "source": "azure"}


def run_llm_backend(file_content, file_name, file_issues, backend, config):
    prompt = build_llm_prompt(file_content, file_issues, file_name)
    if backend == 'local':
        raw_output, model_details = run_local_backend(prompt, config)
    elif backend == 'azure':
        raw_output, model_details = run_azure_backend(prompt, config)
    else:
        raise ValueError(f"Unsupported backend: {backend}")
    extracted_code = extract_python_code(raw_output)
    return extracted_code, raw_output, model_details

# ==== DB WRITER ====

def insert_or_update_record(collection, repo_name, file_path, issues, backend,
                             code_extracted, raw_llm_output, model_details):
    file_name = os.path.basename(file_path)
    timestamp = datetime.datetime.utcnow()
    update_fields = {
        'repo_name': repo_name, 
        'file_name': file_name, 
        'full_file_path': file_path,
        'timestamp': timestamp, 
        'backend_used': backend,
        'issues': issues, 
        'status': 'Success' if code_extracted else 'Failure',
        'model_details': model_details,
        f"llm_output_raw_{backend}": raw_llm_output,
        f"code_extracted_{backend}": code_extracted
    }
    collection.update_one({'repo_name': repo_name, 'file_name': file_name},
                          {'$set': update_fields}, upsert=True)

# ==== SAVE FIXED FILE ====

def save_fixed_file(full_path, fixed_content, backend, config):
    fix_files_flag = config['autofix'].get('fix_files', False)

    if fix_files_flag:
        # Overwrite original file directly
        with open(full_path, 'w') as f:
            f.write(fixed_content)
        logging.info(f"✅ Original file OVERWRITTEN with fixed version: {full_path}")
    else:
        # Keep side-by-side fixed version
        base_dir = os.path.dirname(full_path)
        filename_no_ext, ext = os.path.splitext(os.path.basename(full_path))
        output_file = os.path.join(base_dir, f"{filename_no_ext}_fix_{backend}{ext}")
        with open(output_file, 'w') as f:
            f.write(fixed_content)
        logging.info(f"✅ Fixed file written to: {output_file}")


# ==== DB & FILE CHECKERS ====

def check_db_and_file(collection, repo_name, file_path, backend, repo_base_path):
    file_name = os.path.basename(file_path)
    record = collection.find_one({'repo_name': repo_name, 'file_name': file_name})
    db_present = bool(record and f"llm_output_raw_{backend}" in record and record[f"llm_output_raw_{backend}"])
    
    # filename_no_ext, ext = os.path.splitext(os.path.basename(file_path))
    # fixed_file = f"{filename_no_ext}_fix_{backend}{ext}"
    # fix_path = os.path.join(repo_base_path, os.path.dirname(file_path), fixed_file)
    # fix_file_present = os.path.exists(fix_path)
    
    
    filename_no_ext, ext = os.path.splitext(os.path.basename(file_path))

    if config['autofix'].get('fix_files', False):
        # Fix is done by replacing original file
        fix_path = os.path.join(repo_base_path, file_path)
    else:
        fixed_file = f"{filename_no_ext}_fix_{backend}{ext}"
        fix_path = os.path.join(repo_base_path, os.path.dirname(file_path), fixed_file)
    
    fix_file_present = os.path.exists(fix_path)

    
    
    return db_present, fix_file_present

# ==== COMMON SUMMARY CALCULATOR ====

def calculate_repo_summary(repo, collection, config, backend):
    repo_url = repo['repo_url']
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_path = os.path.join(repo['local_clone_path'], repo_name)
    normalized_path = os.path.join(config['sonarqube']['results_path'], repo_name)
    normalized_file = get_latest_normalized_file(normalized_path)
    if not normalized_file:
        return repo_name, None, None

    issues_by_file = load_issues_by_file(normalized_file)
    summary = []
    for file_path, issues in issues_by_file.items():
        db_present, fix_file_present = check_db_and_file(collection, repo_name, file_path, backend, repo_path)
        action = 'Skip' if db_present and fix_file_present else 'Process'
        summary.append({
            'File Name': os.path.basename(file_path),
            'File Path': file_path,
            '#Issues': len(issues),
            'DB Record': 'Yes' if db_present else 'No',
            'Fix File': 'Yes' if fix_file_present else 'No',
            'Action': action
        })
    return repo_name, issues_by_file, summary

# ==== PRINT SUMMARY ====

def print_summary_table(repo_name, summary, stage):
    print(f"\n========== {stage} Summary for Repo: {repo_name} ==========")
    print("{:<40} {:<10} {:<12} {:<12} {:<10}".format("File Name", "#Issues", "DB Record", "Fix File", "Action"))
    print("-" * 50)
    for row in summary:
        print("{:<40} {:<10} {:<12} {:<12} {:<10}".format(
            row['File Name'], row['#Issues'], row['DB Record'], row['Fix File'], row['Action']))
    print("-" * 50 + "\n")

# ==== MAIN PROCESSING ====

# ==== IGNORE FILE LIST ==== for Azure, token ptu limit, for now tetsing here. needs to be come from external file sourece like dynamically generated excel file
IGNORE_FILES_TOO_LARGE = [
    'scaling_laws.ipynb',
    'transformer_sizing.ipynb',
]


def process_repository(repo, collection, backend):
    repo_name, issues_by_file, pre_summary = calculate_repo_summary(repo, collection, config, backend)
    if issues_by_file is None:
        logging.error("❌ No normalized file found. Skipping repo.")
        return

    logging.info(f"🚀 Processing repo: {repo_name}")
    print_summary_table(repo_name, pre_summary, "Pre-Processing")

    files_to_process = [s for s in pre_summary if s['Action'] == 'Process']
    if not files_to_process:
        logging.info("✅ Nothing to process. All files already analyzed.")
        return

    repo_path = os.path.join(repo['local_clone_path'], repo_name)

    for idx, file_info in enumerate(files_to_process, 1):
        file_path = file_info['File Path']
        full_path = os.path.join(repo_path, file_path)

        if not os.path.exists(full_path):
            logging.warning(f"⚠️ File not found, skipping: {full_path}")
            continue

        with open(full_path, 'r') as f:
            file_content = f.read()

        issues = issues_by_file[file_path]
        logging.info(f"🔧 Processing [{idx}/{len(files_to_process)}]: {file_path}")

        if file_path in IGNORE_FILES_TOO_LARGE:
            print(f"⚠️ Ignoring file: {file_path}")
            continue
        
        
        if config['autofix'].get('dry_run', False):
            logging.info(f"🟡 Dry run: Skipping LLM and DB for {file_path}")
            continue

        extracted_code, raw_output, model_details = run_llm_backend(file_content, file_path, issues, backend, config)
        insert_or_update_record(collection, repo_name, file_path, issues, backend, extracted_code, raw_output, model_details)

        if extracted_code:
            save_fixed_file(full_path, extracted_code, backend, config)
            logging.info(f"✅ Fixed & saved: {file_path}")
        else:
            logging.warning(f"❌ Extraction failed, No Changes Made: {file_path}")

    # Recalculate and display post-processing summary
    _, _, post_summary = calculate_repo_summary(repo, collection, config, backend)
    print_summary_table(repo_name, post_summary, "Post-Processing")

# ==== WRITE FINAL SUMMARY TO EXCEL ====

def write_final_summary_to_excel(all_repos_summaries):
    output_file = "File_Analysis_Full_Summary.xlsx"
    columns_order = ["File Name", "#Issues", "DB Record", "Fix File", "Action"]
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for repo_name, summaries in all_repos_summaries.items():
            # Write PRE summary
            df_pre = pd.DataFrame(summaries['pre'])[columns_order]
            df_pre.to_excel(writer, index=False, sheet_name=(repo_name[:28] + "_Pre"))
            # Write POST summary
            df_post = pd.DataFrame(summaries['post'])[columns_order]
            df_post.to_excel(writer, index=False, sheet_name=(repo_name[:28] + "_Post"))
    logging.info(f"📊 Full Summary exported to Excel: {output_file}")


# ==== MAIN ENTRY ====

def run_sonar_ai_analysis():
    db_config = config['database']
    backend = config['backend']['type']
    collection = connect_to_mongodb(db_config)

    all_summaries = {}

    for repo in config['github']['repos']:
        if repo.get('enabled', True):
            repo_name, issues_by_file, pre_summary = calculate_repo_summary(repo, collection, config, backend)
            if issues_by_file is None:
                continue
            #print_summary_table(repo_name, pre_summary, "Pre-Processing")
            process_repository(repo, collection, backend)
            _, _, post_summary = calculate_repo_summary(repo, collection, config, backend)
            #print_summary_table(repo_name, post_summary, "Post-Processing")
            all_summaries[repo_name] = {'pre': pre_summary, 'post': post_summary}

    write_final_summary_to_excel(all_summaries)

if __name__ == '__main__':
    run_sonar_ai_analysis()
