import sys
sys.path.insert(0, '/home/user/AiOne')

import os
import json
import time
from typing import Dict, List, Any
from backend.toon_utils import TOONConverter

# Try to import openai
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI library not installed. Run: pip install openai")

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


class RealLLMValidation:
    """Validate TOON vs JSON using real OpenAI API calls"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize with OpenAI API key

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (gpt-4o-mini for cost efficiency, gpt-4o for quality)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.toon = TOONConverter()
        self.results = []

        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

        print(f"✅ OpenAI API initialized")
        print(f"   Model: {self.model}")
        print(f"   Estimated cost: $0.10-0.50 for full test suite")
        print()

    def create_test_scenario(self) -> Dict:
        """Create a medical test scenario"""

        # Scenario: Critical patient with sepsis
        patient_data = {
            "patient": {
                "mrn": "MRN-001234",
                "name": "John Smith",
                "age": 58,
                "gender": "M"
            },
            "vital_signs": {
                "bp_systolic": 85,
                "bp_diastolic": 52,
                "heart_rate": 125,
                "respiratory_rate": 28,
                "temperature": 102.8,
                "spo2": 89
            },
            "lab_results": [
                {"test": "WBC", "value": 18.5, "units": "K/uL", "reference": "4.0-11.0", "flag": "HIGH"},
                {"test": "Lactate", "value": 4.2, "units": "mmol/L", "reference": "<2.0", "flag": "HIGH"},
                {"test": "Creatinine", "value": 2.8, "units": "mg/dL", "reference": "0.7-1.3", "flag": "HIGH"},
                {"test": "Procalcitonin", "value": 12.5, "units": "ng/mL", "reference": "<0.5", "flag": "HIGH"}
            ],
            "presentation": "Patient presents with fever, hypotension, altered mental status, and suspected abdominal source"
        }

        # Convert to both formats
        json_format = json.dumps(patient_data, indent=2)
        toon_format = self.toon.encode_to_toon(patient_data)

        # Test questions with expected answer elements
        questions = [
            {
                "question": "What is the most likely diagnosis for this patient?",
                "expected_keywords": ["sepsis", "septic", "shock", "infection"],
                "type": "diagnosis"
            },
            {
                "question": "What is the patient's lactate level and what does it indicate?",
                "expected_keywords": ["4.2", "elevated", "high", "severe", "poor perfusion"],
                "type": "lab_interpretation"
            },
            {
                "question": "List all abnormal vital signs and explain their significance.",
                "expected_keywords": ["hypotension", "85/52", "tachycardia", "125", "fever", "102.8", "hypoxia", "89"],
                "type": "clinical_assessment"
            },
            {
                "question": "What immediate interventions would you recommend?",
                "expected_keywords": ["fluids", "antibiotics", "blood cultures", "vasopressors", "ICU"],
                "type": "treatment_plan"
            }
        ]

        return {
            "name": "Septic Shock Patient",
            "data": patient_data,
            "json": json_format,
            "toon": toon_format,
            "questions": questions
        }

    def ask_llm(self, data_format: str, format_name: str, question: str) -> Dict:
        """
        Ask LLM a question with data in specified format

        Returns response with timing and token usage
        """
        prompt = f"""You are a medical AI assistant analyzing patient data.

Patient Data ({format_name} format):
{data_format}

Question: {question}

Provide a clear, accurate answer based on the data provided."""

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical AI assistant. Provide accurate, evidence-based answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500
            )

            elapsed_time = time.time() - start_time

            answer = response.choices[0].message.content

            return {
                "answer": answer,
                "tokens_prompt": response.usage.prompt_tokens,
                "tokens_completion": response.usage.completion_tokens,
                "tokens_total": response.usage.total_tokens,
                "time_seconds": elapsed_time,
                "model": response.model
            }

        except Exception as e:
            return {
                "error": str(e),
                "answer": None
            }

    def evaluate_answer(self, answer: str, expected_keywords: List[str]) -> Dict:
        """Evaluate answer quality based on expected keywords"""
        if not answer:
            return {"score": 0, "found_keywords": [], "missing_keywords": expected_keywords}

        answer_lower = answer.lower()
        found = []
        missing = []

        for keyword in expected_keywords:
            if keyword.lower() in answer_lower:
                found.append(keyword)
            else:
                missing.append(keyword)

        score = len(found) / len(expected_keywords) if expected_keywords else 1.0

        return {
            "score": score,
            "found_keywords": found,
            "missing_keywords": missing
        }

    def compare_responses(self, json_resp: Dict, toon_resp: Dict, expected_keywords: List[str]) -> Dict:
        """Compare JSON vs TOON responses"""

        # Evaluate both
        json_eval = self.evaluate_answer(json_resp.get("answer"), expected_keywords)
        toon_eval = self.evaluate_answer(toon_resp.get("answer"), expected_keywords)

        # Compare
        return {
            "json_score": json_eval["score"] * 100,
            "toon_score": toon_eval["score"] * 100,
            "difference": (toon_eval["score"] - json_eval["score"]) * 100,
            "json_found": json_eval["found_keywords"],
            "toon_found": toon_eval["found_keywords"],
            "json_missing": json_eval["missing_keywords"],
            "toon_missing": toon_eval["missing_keywords"],
            "json_tokens": json_resp.get("tokens_total", 0),
            "toon_tokens": toon_resp.get("tokens_total", 0),
            "token_savings": json_resp.get("tokens_prompt", 0) - toon_resp.get("tokens_prompt", 0)
        }

    def run_test(self):
        """Run full validation test"""
        print("=" * 80)
        print("REAL LLM API VALIDATION: TOON vs JSON")
        print("=" * 80)
        print()
        print(f"Model: {self.model}")
        print()

        scenario = self.create_test_scenario()

        print(f"Test Scenario: {scenario['name']}")
        print("-" * 80)
        print()

        # Show data samples
        print("JSON Format:")
        print(scenario['json'][:200] + "...")
        print(f"Length: {len(scenario['json'])} chars")
        print()

        print("TOON Format:")
        print(scenario['toon'][:200] + "...")
        print(f"Length: {len(scenario['toon'])} chars")
        print()

        token_savings_pct = ((len(scenario['json']) - len(scenario['toon'])) / len(scenario['json']) * 100)
        print(f"Character savings (TOON): {token_savings_pct:+.1f}%")
        print()

        # Test each question
        all_results = []

        for i, q in enumerate(scenario['questions'], 1):
            print("=" * 80)
            print(f"QUESTION {i}/{len(scenario['questions'])}: {q['type']}")
            print("=" * 80)
            print()
            print(f"Q: {q['question']}")
            print()

            # Ask with JSON
            print("Testing JSON format...")
            json_response = self.ask_llm(scenario['json'], "JSON", q['question'])

            # Small delay to avoid rate limits
            time.sleep(0.5)

            # Ask with TOON
            print("Testing TOON format...")
            toon_response = self.ask_llm(scenario['toon'], "TOON", q['question'])

            print()

            # Compare
            comparison = self.compare_responses(json_response, toon_response, q['expected_keywords'])

            # Display results
            print("-" * 80)
            print("RESULTS:")
            print("-" * 80)
            print()

            print(f"JSON Response:")
            print(f"  Answer: {json_response.get('answer', 'ERROR')[:150]}...")
            print(f"  Score: {comparison['json_score']:.1f}%")
            print(f"  Found keywords: {comparison['json_found']}")
            print(f"  Prompt tokens: {json_response.get('tokens_prompt', 0)}")
            print()

            print(f"TOON Response:")
            print(f"  Answer: {toon_response.get('answer', 'ERROR')[:150]}...")
            print(f"  Score: {comparison['toon_score']:.1f}%")
            print(f"  Found keywords: {comparison['toon_found']}")
            print(f"  Prompt tokens: {toon_response.get('tokens_prompt', 0)}")
            print()

            print(f"Comparison:")
            print(f"  Accuracy difference: {comparison['difference']:+.1f}%")
            print(f"  Token savings (prompt): {comparison['token_savings']} tokens")

            if abs(comparison['difference']) < 10:
                verdict = "✅ EQUIVALENT - No significant difference"
            elif comparison['difference'] > 10:
                verdict = f"✅ TOON BETTER by {comparison['difference']:.1f}%"
            else:
                verdict = f"⚠️  JSON BETTER by {abs(comparison['difference']):.1f}%"

            print(f"  Verdict: {verdict}")
            print()

            all_results.append({
                'question': q['question'],
                'type': q['type'],
                'comparison': comparison,
                'json_response': json_response,
                'toon_response': toon_response
            })

            # Small delay between questions
            time.sleep(0.5)

        # Overall summary
        print("=" * 80)
        print("OVERALL RESULTS")
        print("=" * 80)
        print()

        avg_json_score = sum(r['comparison']['json_score'] for r in all_results) / len(all_results)
        avg_toon_score = sum(r['comparison']['toon_score'] for r in all_results) / len(all_results)
        total_token_savings = sum(r['comparison']['token_savings'] for r in all_results)
        total_json_tokens = sum(r['json_response'].get('tokens_total', 0) for r in all_results)
        total_toon_tokens = sum(r['toon_response'].get('tokens_total', 0) for r in all_results)

        print(f"Questions Tested: {len(all_results)}")
        print()
        print(f"Average JSON Accuracy: {avg_json_score:.1f}%")
        print(f"Average TOON Accuracy: {avg_toon_score:.1f}%")
        print(f"Accuracy Difference: {avg_toon_score - avg_json_score:+.1f}%")
        print()
        print(f"Total Tokens Used:")
        print(f"  JSON: {total_json_tokens} tokens")
        print(f"  TOON: {total_toon_tokens} tokens")
        print(f"  Savings: {total_json_tokens - total_toon_tokens} tokens ({((total_json_tokens - total_toon_tokens) / total_json_tokens * 100):+.1f}%)")
        print()

        # Breakdown by question type
        print("By Question Type:")
        print("-" * 60)
        for result in all_results:
            qtype = result['type']
            comp = result['comparison']
            print(f"{qtype:20} JSON: {comp['json_score']:5.1f}%  TOON: {comp['toon_score']:5.1f}%  Diff: {comp['difference']:+6.1f}%")

        print()
        print("=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print()

        if abs(avg_toon_score - avg_json_score) < 5:
            print("✅ NO SIGNIFICANT ACCURACY DIFFERENCE")
            print(f"   TOON and JSON produce equivalent results ({abs(avg_toon_score - avg_json_score):.1f}% difference)")
            print(f"   Token savings: {((total_json_tokens - total_toon_tokens) / total_json_tokens * 100):.1f}%")
            print()
            print("✅ TOON IS VALIDATED FOR PRODUCTION USE WITH LLMs")
            print()
        elif avg_toon_score > avg_json_score + 5:
            print("✅ TOON SHOWS BETTER ACCURACY")
            print(f"   TOON: {avg_toon_score:.1f}%")
            print(f"   JSON: {avg_json_score:.1f}%")
            print(f"   Improvement: +{avg_toon_score - avg_json_score:.1f}%")
            print()
            print("✅ TOON IS RECOMMENDED FOR PRODUCTION USE")
            print()
        else:
            print("⚠️  JSON SHOWS BETTER ACCURACY")
            print(f"   JSON: {avg_json_score:.1f}%")
            print(f"   TOON: {avg_toon_score:.1f}%")
            print(f"   Difference: {avg_json_score - avg_toon_score:.1f}%")
            print()
            print("⚠️  CONSIDER MORE TESTING BEFORE PRODUCTION USE")
            print()

        # Cost estimate
        # GPT-4o-mini: ~$0.15/1M input, ~$0.60/1M output
        input_cost = total_json_tokens * 0.15 / 1_000_000 + total_toon_tokens * 0.15 / 1_000_000
        output_tokens = sum(r['json_response'].get('tokens_completion', 0) + r['toon_response'].get('tokens_completion', 0) for r in all_results)
        output_cost = output_tokens * 0.60 / 1_000_000
        total_cost = input_cost + output_cost

        print(f"Test Cost:")
        print(f"  Total tokens: {total_json_tokens + total_toon_tokens + output_tokens:,}")
        print(f"  Estimated cost: ${total_cost:.4f}")
        print()

        return {
            'avg_json_score': avg_json_score,
            'avg_toon_score': avg_toon_score,
            'difference': avg_toon_score - avg_json_score,
            'token_savings_pct': ((total_json_tokens - total_toon_tokens) / total_json_tokens * 100),
            'total_cost': total_cost,
            'results': all_results
        }


def main():
    """Run real LLM validation"""

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("=" * 80)
        print("ERROR: OpenAI API key not found")
        print("=" * 80)
        print()
        print("Please set your OpenAI API key:")
        print()
        print("Option 1: Environment variable")
        print("  export OPENAI_API_KEY='your-key-here'")
        print()
        print("Option 2: .env file")
        print("  echo 'OPENAI_API_KEY=your-key-here' > .env")
        print()
        print("Then run this script again.")
        print()
        return False

    try:
        # Use gpt-4o-mini for cost efficiency
        # Change to "gpt-4o" for higher quality but 10x cost
        validator = RealLLMValidation(model="gpt-4o-mini")
        result = validator.run_test()
        return True

    except Exception as e:
        print(f"❌ Error running validation: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
