
# 🔧 Automated Sonar AI Code Analyzer & AutoFixer

> **AI-powered multi-repository SonarQube remediation pipeline with hybrid LLM backends (Local + Azure OpenAI), full audit tables, and automatic cloning capabilities.**

---

## 🚀 Project Background

Modern software teams constantly struggle with growing SonarQube technical debt across multiple repositories. This solution fully automates:

- Repository scanning via SonarQube
- Auto-cloning repositories directly from GitHub
- Normalizing, parsing, and classifying Sonar issues
- Leveraging local and cloud LLMs to generate high-confidence autofixes
- Producing detailed audit tables comparing fixes from multiple AI models
- Generating comprehensive audit files and metrics

The system supports **air-gapped execution with fully local Ollama models** or cloud-based Azure OpenAI models as desired.

---

## 🎯 Key Features

- ✅ Multi-repository orchestration with auto-cloning
- ✅ SonarQube deep integration and issue normalization
- ✅ Hybrid LLM backend (Ollama local, Azure OpenAI)
- ✅ Side-by-side fix comparison and audit metrics
- ✅ Full database traceability and dashboards
- ✅ Configurable YAML-based pipeline control
- ✅ Supports multiple programming languages (Python, YAML, IPython notebooks, etc.)
- ✅ Air-gapped fully local option (CPU or GPU with Ollama)

---

## 📊 Live Metrics for Sample repositories — Before & After AI Fixes (Multi-backend Comparison)

### **agentic-ai-email-assistant**

| Metric | Pre-Fix | Local CodeWizard | Azure-4o | Azure-4o-mini | Local % | Azure-4o % | Azure-4o-mini % |
|--------|---------|-----------------|----------|---------------|---------|------------|------------------|
| Reliability | 8 | 8 | 0 | 0 | **0%** | **100% ↓** | **100% ↓** |
| Maintainability | 26 | 13 | 4 | 4 | **50% ↓** | **85% ↓** | **85% ↓** |
| Duplication | 3.9% | 2.6% | 3.9% | 3.9% | **33% ↓** | **0%** | **0%** |

---

### **private-gpt**

| Metric | Pre-Fix | Local CodeWizard | Azure-4o | Azure-4o-mini | Local % | Azure-4o % | Azure-4o-mini % |
|--------|---------|-----------------|----------|---------------|---------|------------|------------------|
| Reliability | 3 | 0 | 0 | 1 | **100% ↓** | **100% ↓** | **0%** |
| Maintainability | 88 | 62 | 39 | 51 | **30% ↓** | **56% ↓** | **42% ↓** |
| Duplication | 0.7% | 0% | 0.7% | 0.7% | **100% ↓** | **0% ↓** | **0% ↓** |

---

## 🔎 Overall Compact Audit Verdict Summary

| Parameter | Local-Ollama (CodeWizard) | Azure GPT-4o-mini | Azure GPT-4o |
|-----------|------------------------|--------------------|--------------|
| Fix Coverage | Partial (~70-80%) | High (~95-98%) | ✅ Near-Perfect |
| Logic Safety | ✅ Safe | ✅ Consistently safe | ✅ Consistently safe |
| Output Safety | Minor inconsistencies | ✅ Very clean | ✅ Excellent output |
| Extraneous Changes | Minimal | ✅ Very controlled | ✅ Minimal and safe |
| Cognitive Complexity Fixes | Sometimes partial | ✅ Almost complete | ✅ Complete |
| Architecture Suggestions | Limited | Moderate | ✅ Best improvements |
| Best Use Case | Local small fixes | Good compromise | ✅ Production-grade fixes |

---

## ⚙ Quick Start Setup

### 1️⃣ Install SonarQube

- Download: https://www.sonarqube.org/downloads/
- Launch local SonarQube instance (default `localhost:9000`)
- Generate your SonarQube admin token

### 2️⃣ Install Ollama (Local Model Server)

- Install Ollama: https://ollama.com/download
- Pull models locally:

```bash
ollama pull wizardcoder:33b-v1
```

### 3️⃣ Clone This Repository

```bash
git clone https://github.com/Saurabh11811/AutoSonarFixer-P.git
cd AutoSonarFixer-P
```

### 4️⃣ Install Python Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5️⃣ Create `config.yaml` (Full Config Control)

Sample config structure:

```yaml
backend:
  type: local

autofix:
  dry_run: false
  fix_files: true
  model: wizardcoder:33b
  temperature: 0.1
  output_suffix: _fix

azure:
  deployment: gpt-4o
  endpoint: https://your-endpoint.openai.azure.com/
  key: <your-azure-api-key>
  version: 2024-10-21

database:
  type: mongodb
  host: localhost
  port: 27017
  db_name: sonar_db
  collection: Analysis_Sonar

sonarqube:
  server_url: http://localhost:9000
  auth_token: <your-sonar-token>
  scanner_path: /opt/homebrew/bin/sonar-scanner
  results_path: ./results/sonar_reports/
  java_home: /Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home

github:
  repos:
  - repo_url: https://github.com/Saurabh11811/agentic-ai-email-assistant
    local_clone_path: /Users/YourUser/repo/
    enabled: true
    api_token: ''
```

- ✅ The system **automatically clones repositories** from GitHub prior to analysis.

### 6️⃣ Run the Orchestrator

```bash
python main_orchestrator.py
```

### 7️⃣ Run the Analyzer (still separate run due to long-running process)

```bash
python phase5_autofix/sonar_ai_analyzer.py
```

### 8️⃣ Run the Sonar Scanner again to check the updated results on SonarQube dashboard

```bash
python phase4_sonar_scan/sonar_scanner.py
```


---

## 🔬 Supported AI Backends

| Backend | Model | Notes |
|---------|--------|--------|
| Ollama (Local) | WizardCoder-33B | Fully offline |
| Azure OpenAI | GPT-4o / GPT-4o-mini | Highest cloud accuracy |

---


## 🤝 TODOs!

- 🔧 Additional backend integrations
- 📊 Enhanced dashboards & visualization
- 🧪 Regression test suites
- 🌐 New language support
- 🔬 Advanced prompt tuning



