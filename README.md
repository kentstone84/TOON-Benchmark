# 💰 LLM Cost Optimization: TOON vs. JSON Benchmark (OpenAI API)

A real-world validation demonstrating how switching from **JSON** to **TOON (Token-Oriented Object Notation)** for structuring LLM prompts achieves significant cost savings and bandwidth reduction with **zero loss in clinical accuracy**.

---

## 🚀 Project Overview & Key Findings

This repository contains the benchmark script (`test_llm_real_api_validation.py`) used to compare the token efficiency and output accuracy of two data formats when passed to the **OpenAI GPT-4o-mini** model for a clinical decision support task (Septic Shock Patient Analysis).

| Metric | Baseline (JSON) | Optimized (TOON) | Improvement | Status |
| :--- | :---: | :---: | :---: | :--- |
| **Clinical Accuracy** | 86.9% | 86.9% | **0.0% Difference** | ✅ **Validated** |
| **Prompt Token Savings** | 398 tokens/query (Avg.) | 264 tokens/query (Avg.) | **-33.7%** | ✅ **Validated** |
| **Total Token Savings** | 2,973 tokens/test | 2,428 tokens/test | **-18.3%** | ✅ **Validated** |
| **Data Transfer (Chars)** | 943 chars/payload | 486 chars/payload | **-48.5%** | ✅ **Validated** |
| **Projected Enterprise Savings** | N/A | N/A | **\$10K - \$179K/yr** (at scale) | ✅ **Projected** |

### Why TOON Wins

TOON is specifically designed to minimize the use of repetitive characters (quotes, commas, braces) that the LLM tokenizer (`tiktoken`) counts as cost. For structured, repetitive data common in enterprise AI (logs, patient records, financial transactions), this reduction is substantial and direct.

---

## 🛠️ How to Run the Benchmark

### 1. Prerequisites

* Python 3.8+
* An OpenAI API Key
* The `backend/toon_utils.py` file (which contains the `TOONConverter` class) must be present in your environment.

### 2. Setup

```bash
# Clone the repository
git clone [YOUR-REPO-LINK-HERE]
cd [YOUR-REPO-NAME]

# Install required libraries
pip install openai python-dotenv tiktoken

# Set your API Key (Highly Recommended)
export OPENAI_API_KEY='sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
# Alternatively, create a .env file and add: OPENAI_API_KEY='your-key-here'
