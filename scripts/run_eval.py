#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys path to import internal modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.pipeline import rag_pipeline
from src.evaluation.ragas_eval import evaluate_rag, format_scores_for_display

def main():
    print("="*60)
    print("  Running RAGAS Evaluation on Pipeline")
    print("="*60)
    
    questions = [
        "What should I do during a flood?",
        "How can I protect myself from a heatwave?"
    ]
    
    ground_truths = [
        "Evacuate to higher ground immediately. Follow warnings and coordinate with the Emergency Operations Center.",
        "Stay indoors, drink plenty of water, avoid strenuous activities, and recognize signs of heat stroke."
    ]
    
    outputs = []
    for q in questions:
        print(f"\n[*] Querying Pipeline: '{q}'")
        res = rag_pipeline.run(q)
        outputs.append(res)
        
    print("\n[*] Running RAGAS Metrics (Faithfulness, Relevancy, Precision, Recall)...")
    print("    (This uses LLM-as-a-judge and may take a minute)")
    
    scores = evaluate_rag(outputs, ground_truths=ground_truths, save_results=True)
    
    print("\n" + "="*60)
    print(format_scores_for_display(scores))
    print("="*60)

if __name__ == "__main__":
    main()
