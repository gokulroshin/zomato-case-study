import os
from app.data import load_dataset, preprocess, filter_candidates
from app.models.preferences import UserPreferences, BudgetTier
from app.llm import build_messages, parse_groq_response, GroqClient

def main():
    print("Loading and preprocessing dataset...")
    df = preprocess(load_dataset())
    
    # Budget 1500 for two -> high tier
    prefs = UserPreferences(
        location="Bellandur",
        min_rating=4.2,
        budget=BudgetTier.high,
        top_n=5
    )
    
    print(f"Filtering for Location={prefs.location}, Min Rating={prefs.min_rating}, Budget={prefs.budget.value}...")
    filter_result = filter_candidates(df, prefs)
    print(f"Filter returned {filter_result.total_matches} matches.")
    
    if filter_result.is_empty:
        print("No candidates found. Reason:", filter_result.reason)
        return

    print("Building prompt for Groq...")
    messages = build_messages(prefs, filter_result.candidates)
    
    client = GroqClient()
    print("Calling Groq LLM...")
    try:
        response_text = client.chat(messages)
        print("Groq Response received. Parsing...")
        summary, recs = parse_groq_response(response_text, filter_result.candidates, prefs.top_n)
        
        print("\n=== FINAL RECOMMENDATIONS ===")
        print("Summary:", summary)
        for r in recs:
            print(f"{r.rank}. {r.restaurant_name} (Rating: {r.rating}, Cost: {r.estimated_cost})")
            print(f"   Explanation: {r.explanation}")
            
    except Exception as e:
        print("Error during LLM invocation:")
        print(e)

if __name__ == "__main__":
    main()
