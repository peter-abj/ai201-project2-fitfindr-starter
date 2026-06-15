"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    import re

    session = _new_session(query, wardrobe)

    # Step 2: Parse query for description, size, max_price
    # Strategy: regex to find "under $X" or "$X" patterns for price,
    # "size X" or "size: X" for size, and everything else as description
    query_lower = query.lower()

    # Extract price: look for "under $X" or "$X"
    price_match = re.search(r'(?:under\s+)?\$(\d+(?:\.\d{2})?)', query_lower)
    max_price = float(price_match.group(1)) if price_match else None

    # Extract size: look for "size X" or "size: X" (case-insensitive)
    size_match = re.search(r'size[\s:]+([A-Za-z0-9/]+)', query_lower)
    size = size_match.group(1).upper() if size_match else None

    # Description: everything else (remove price and size phrases)
    description = query
    if price_match:
        description = description.replace(price_match.group(0), "").strip()
    if size_match:
        description = description.replace(size_match.group(0), "").strip()
    description = description.strip()

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # Step 3: Call search_listings
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    # Check if search returned results
    if not results:
        session["error"] = (
            "Sorry, I couldn't find anything matching that description at that price point. "
            "Try a broader search, a higher budget, or tell me what styles you're into!"
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5: Call suggest_outfit
    outfit_suggestion = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    # Check if wardrobe was empty (suggest_outfit returns a specific message)
    if wardrobe.get("items") is None or len(wardrobe.get("items", [])) == 0:
        # Note: suggest_outfit still returns a string (general advice), but we note this in session
        # The agent doesn't stop here — it continues to create_fit_card
        pass

    # Step 6: Call create_fit_card
    fit_card = create_fit_card(outfit_suggestion, session["selected_item"])
    session["fit_card"] = fit_card

    # Step 7: Return the session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
