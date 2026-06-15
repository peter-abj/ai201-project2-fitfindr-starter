"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    listings = load_listings()

    # Parse search keywords
    keywords = description.lower().split()

    # Filter and score
    candidates = []
    for listing in listings:
        # Price filter
        if max_price is not None and listing["price"] > max_price:
            continue

        # Size filter (case-insensitive substring match)
        if size is not None:
            if size.upper() not in listing["size"].upper():
                continue

        # Keyword scoring: count matches in title, description, style_tags, brand
        searchable = (
            listing["title"].lower() + " " +
            listing["description"].lower() + " " +
            " ".join(listing.get("style_tags", [])).lower() + " " +
            (listing.get("brand") or "").lower()
        )

        score = sum(1 for kw in keywords if kw in searchable)

        # Only include listings with at least one keyword match
        if score > 0:
            candidates.append((score, listing))

    # Sort by score (highest first), then by price (lowest first as tiebreaker)
    candidates.sort(key=lambda x: (-x[0], x[1]["price"]))

    return [listing for score, listing in candidates]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    client = _get_groq_client()

    # Format the new item for the prompt
    new_item_desc = f"{new_item['title']} ({new_item['category']}, {', '.join(new_item.get('colors', []))})"

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        # Empty wardrobe: provide general styling advice
        prompt = f"""You are a fashion stylist. The user is considering buying this item:

{new_item_desc}

Style tags: {', '.join(new_item.get('style_tags', []))}

The user hasn't told us about their existing wardrobe yet, so give them general styling advice:
- What types of pieces pair well with this item?
- What vibe or aesthetic does this evoke?
- Suggest 2-3 specific styling ideas (e.g., "pair with baggy jeans for a 90s look")

Be conversational and specific. 2-3 sentences max."""

    else:
        # Format wardrobe items for the prompt
        wardrobe_desc = "\n".join(
            f"- {item['name']} ({item['category']}, colors: {', '.join(item.get('colors', []))})"
            for item in wardrobe_items
        )

        prompt = f"""You are a fashion stylist. The user is considering buying this item:

{new_item_desc}
Style tags: {', '.join(new_item.get('style_tags', []))}

Their current wardrobe includes:
{wardrobe_desc}

Suggest a complete outfit using this new item and pieces from their wardrobe. Name specific wardrobe items by name. Include:
- Which wardrobe pieces to pair with the new item
- Specific styling tips (e.g., "tuck it in", "roll the sleeves", "wear it oversized")
- What aesthetic or vibe this outfit creates

Be conversational and specific. 3-4 sentences."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback if LLM fails
        if wardrobe_items:
            return "Pair this with neutral bottoms and simple shoes for a versatile everyday look."
        else:
            return "This piece pairs well with basics like jeans or trousers and neutral shoes — go for a timeless, wearable vibe!"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    """
    if not outfit or not outfit.strip():
        return "I need a complete outfit suggestion to write a fit card. Please try again!"

    client = _get_groq_client()

    item_name = new_item.get("title", "this piece")
    price = new_item.get("price", "??")
    platform = new_item.get("platform", "thrifted")

    prompt = f"""Write a short, casual Instagram/TikTok fit card caption for someone who just bought this thrifted item:

Item: {item_name}
Price: ${price}
Platform: {platform}

The outfit they're styling it with: {outfit}

Requirements:
- Be casual and authentic — sound like a real person posting an OOTD, not a product description
- Mention the item name, price, and platform naturally (once each)
- Use 1-2 emojis max
- 2-4 sentences
- Feel excited and personal

Caption:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # Higher temperature for variety
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback if LLM fails
        return f"just copped this {item_name} from {platform} for ${price} and it's already my favorite 🖤"
