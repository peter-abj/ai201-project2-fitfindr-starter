# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Filters the mock listings dataset by description keywords, clothing size, and maximum price. Returns a ranked list of matching items sorted by relevance (keyword match strength and recency/condition).

**Input parameters:**
- `description` (str): Free-text search query (e.g., "vintage graphic tee", "oversized blazer"). Searches against title, description, style_tags, and brand fields.
- `size` (str): Clothing size to filter by (e.g., "M", "W30", "S/M", "One Size"). Returns listings where the item's size matches or is compatible. Optional — if omitted, all sizes included.
- `max_price` (float): Maximum price threshold. Returns listings where price ≤ max_price. Optional — if omitted, all prices included.

**What it returns:**
A list of listing dictionaries, sorted by relevance (best matches first). Each listing includes: id, title, description, category, style_tags, size, condition, price, colors, brand, platform. If no results match, returns an empty list `[]`.

**What happens if it fails or returns nothing:**
If the search returns no listings (empty list), the agent sets an error message ("Sorry, I couldn't find anything matching that description at that price point. Try a broader search or a higher budget.") in session state and stops the planning loop. It does NOT call suggest_outfit with empty input.

---

### Tool 2: suggest_outfit

**What it does:**
Takes a newly found listing item and the user's existing wardrobe, then generates a styled outfit recommendation. Uses color harmony, style tag compatibility, and category balance (top + bottom + outerwear/shoes) to suggest which wardrobe items pair well with the new piece. Includes specific styling tips (e.g., "roll the sleeves once and tuck the front corner").

**Input parameters:**
- `new_item` (dict): A single listing object from search_listings results. Must include: id, title, category, colors, style_tags, price, condition. Example: `{"id": "lst_006", "title": "Graphic Tee — 2003 Tour Bootleg Style", "category": "tops", "colors": ["black"], "style_tags": ["graphic tee", "vintage", "grunge"], ...}`
- `wardrobe` (dict): The user's wardrobe. Must be in the format `{"items": [...]}` where each item includes: id, name, category, colors, style_tags, notes. Can be empty (`{"items": []}`).

**What it returns:**
A string containing a styled outfit recommendation. Example: "Pair this black graphic tee with your baggy straight-leg dark wash jeans and chunky white sneakers for an authentic 90s grunge vibe. Leave it untucked for that relaxed fit. Add your black crossbody bag for a complete look."

**What happens if it fails or returns nothing:**
If the wardrobe is empty (no items), the agent tells the user: "I'd love to style this for you, but I need to know more about your existing wardrobe first! What bottoms, shoes, and outerwear do you usually wear?" and stops without calling create_fit_card. If the suggestion logic fails internally, return a generic fallback: "Pair this with neutral bottoms and simple sneakers or boots for a versatile everyday look."

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the new listing item, then generates a social-media-style fit card caption that a user could post on Instagram or TikTok. Mimics authentic thrifter language, includes emoji, mentions where the item was bought and the price, and hypes the outfit in a casual, relatable way.

**Input parameters:**
- `outfit` (str): The outfit suggestion text returned from suggest_outfit(). Example: "Pair this black graphic tee with your baggy jeans..."
- `new_item` (dict): The listing object from search_listings. Must include at least: title, price, platform. Example: `{"title": "Graphic Tee", "price": 24.00, "platform": "depop", ...}`

**What it returns:**
A string containing a social-media fit card caption. Example: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 pair with your baggy jeans for peak 90s energy. full look in my stories"

**What happens if it fails or returns nothing:**
If outfit is empty or missing, return an error message: "I need a complete outfit suggestion to write a fit card. Please try again!" If new_item is missing price or platform, use defaults ("thrifted" and "$XX"). If the LLM fails to generate caption, return a fallback: "just got this [title] from [platform] and it's fire 🔥 so good"

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The planning loop follows a strict sequential flow with early-exit error handling:

1. **Parse user input** — Extract search parameters (description, size, max_price) from the user's message.
2. **Call search_listings()** — Execute with the parsed parameters.
3. **Check if search succeeded** — 
   - If `results == []` (empty list): Set `session['error'] = "No listings found..."` and **return early** to the user with the error message. Do NOT proceed to suggest_outfit.
   - If `results != []`: Set `session['selected_item'] = results[0]` (the top match) and proceed to Step 4.
4. **Call suggest_outfit()** — Pass `new_item=session['selected_item']` and `wardrobe=user_wardrobe` to the function.
5. **Check wardrobe validity** —
   - If wardrobe is empty: Set `session['error'] = "Need wardrobe info..."` and **return early**. Do NOT proceed to create_fit_card.
   - If outfit suggestion returned: Set `session['outfit_suggestion'] = suggestion` and proceed to Step 6.
6. **Call create_fit_card()** — Pass `outfit=session['outfit_suggestion']` and `new_item=session['selected_item']`.
7. **Finalize session** — Set `session['fit_card'] = card_output` and return the complete session to the user.

The agent is "done" when all three tools have executed successfully OR when an error condition is hit at any step. The agent never recovers from an error — it tells the user what went wrong and offers a specific suggestion for how to fix their input.

---

## State Management

**How does information from one tool get passed to the next?**

A `session` dictionary persists across all tool calls within a single user interaction. The session keys are:

- `selected_item` (dict or None): The listing object returned from search_listings (specifically, results[0]). Passed to suggest_outfit() and create_fit_card().
- `outfit_suggestion` (str or None): The outfit text returned from suggest_outfit(). Passed to create_fit_card().
- `fit_card` (str or None): The fit card caption returned from create_fit_card(). Included in final response.
- `error` (str or None): If any tool fails or returns invalid data, set this to a user-facing error message. When error is set, the planning loop stops and returns the error to the user instead of continuing.
- `user_wardrobe` (dict): Provided by the user at the start or stored from a previous session. Passed to suggest_outfit().

The flow ensures that search_listings' output becomes suggest_outfit's input, and suggest_outfit's output becomes create_fit_card's input. If any tool fails or returns empty/None, the error field is set and the remaining tools are NOT called.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set session['error'] = "Sorry, I couldn't find anything matching that description at that price point. Try broadening your search or increasing your budget — or let me know what styles you're into and I can suggest items you might love." Stop the planning loop. Do NOT call suggest_outfit. |
| suggest_outfit | Wardrobe is empty (no items in user's wardrobe) | Set session['error'] = "I'd love to style this for you, but I need to know more about your wardrobe first! Tell me about the bottoms, shoes, and outerwear you usually wear, and I'll put together an outfit." Stop the planning loop. Do NOT call create_fit_card. |
| create_fit_card | Outfit string is empty or None | Return fallback: "just got [title] from [platform] for $[price] and already obsessed 🔥 feel like it's gonna be so good with my existing fits" (uses new_item fields to fill blanks). |
| LLM service failure (suggest_outfit or create_fit_card) | Groq API is unavailable or returns error | Return a generic fallback response using the data at hand (no LLM call). For suggest_outfit: "Pair this with neutral bottoms and sneakers for a versatile everyday look." For create_fit_card: "just copped this off [platform] and it's already my favorite 🖤" |

---

## Architecture

```
                              User Query
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │   Planning Loop     │
                        │  (run_agent)        │
                        └─────────┬───────────┘
                                  │
                        ┌─────────▼──────────────┐
                        │ search_listings()      │
                        │ (description, size,    │
                        │  max_price)            │
                        └─────────┬──────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │ results == [] ?    │
                        └────┬──────────┬────┘
                             │          │
                          YES│          │NO
                             │          │
                    ┌────────▼──┐       └──────────────┐
                    │ [ERROR]   │        session['selected_item']
                    │ Return    │        = results[0]
                    │ error msg │
                    │ STOP      │        │
                    └───────────┘        ▼
                                ┌─────────────────────┐
                                │ suggest_outfit()    │
                                │ (selected_item,     │
                                │  wardrobe)          │
                                └────────┬────────────┘
                                         │
                            ┌────────────▼──────────┐
                            │ wardrobe empty?       │
                            └────┬──────────┬───────┘
                                 │          │
                              YES│          │NO
                                 │          │
                        ┌────────▼──┐       └─────────────┐
                        │ [ERROR]   │    session['outfit_
                        │ Return    │     suggestion']
                        │ error msg │    = suggestion
                        │ STOP      │
                        └───────────┘     │
                                          ▼
                                ┌─────────────────────┐
                                │ create_fit_card()   │
                                │ (outfit,            │
                                │  new_item)          │
                                └────────┬────────────┘
                                         │
                            ┌────────────▼──────────┐
                            │ outfit empty?         │
                            └────┬──────────┬───────┘
                                 │          │
                              YES│          │NO
                                 │          │
                        ┌────────▼──────┐   └─────────────┐
                        │ Fallback      │   session['fit_
                        │ caption       │    card'] =
                        └────────┬──────┘   card_output
                                 │          │
                                 └────┬─────┘
                                      ▼
                           ┌──────────────────────┐
                           │ Return Session Dict  │
                           │ (to user via Gradio) │
                           └──────────────────────┘

LEGEND:
- Boxes: Tools or decision points
- Arrows: Data flow or control flow
- [ERROR] paths: Early exit branches that stop the loop
- Session State: selected_item, outfit_suggestion, fit_card, error, user_wardrobe
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

**search_listings():**
- AI tool: Claude
- Input: Tool 1 spec block (what it does, parameters, return value, failure mode), load_listings() function signature from utils/data_loader.py
- Expected output: A Python function that (1) loads all listings via load_listings(), (2) filters by description (keyword search in title + style_tags), (3) filters by size (exact or compatible match), (4) filters by max_price, (5) sorts by relevance (matching keywords first), (6) returns results as a list or empty list
- Verification: Test against 3 queries: (a) "vintage graphic tee", size=None, max_price=50 — should return 2+ results; (b) "vintage graphic tee", size="S", max_price=20 — should return 1 result (lst_002); (c) "designer ballgown", size="XXS", max_price=5 — should return empty list []

**suggest_outfit():**
- AI tool: Claude
- Input: Tool 2 spec block, Groq API setup instructions (model: llama-3.3-70b-versatile, get API key from .env), example wardrobe from wardrobe_schema.json, and a note about LLM failure fallback
- Expected output: A Python function that (1) checks if wardrobe['items'] is empty and returns error message, (2) constructs a prompt to the LLM with the new_item and wardrobe details, (3) calls Groq API with the prompt, (4) returns the LLM's suggestion or a fallback if LLM fails
- Verification: (a) Test with example wardrobe + a new item — should return a non-empty suggestion string; (b) Test with empty wardrobe — should return the specific error message; (c) Test LLM failure — should not crash, return fallback instead

**create_fit_card():**
- AI tool: Claude
- Input: Tool 3 spec block, example fit card captions (casual Instagram style), Groq API setup, note about LLM temperature (increase if responses are too repetitive)
- Expected output: A Python function that (1) checks if outfit is empty and returns error message, (2) constructs a prompt to the LLM with outfit + new_item (including price, platform, title), (3) calls Groq API with temperature=0.8, (4) returns the fit card caption or fallback if LLM fails
- Verification: (a) Test with a complete outfit + new_item — should return a fit card caption under 280 characters; (b) Test with empty outfit — should return error message; (c) Run 3 times on the same input — captions should vary (not identical)

**Milestone 4 — Planning loop and state management:**

**run_agent() in agent.py:**
- AI tool: Claude
- Input: Architecture diagram (ASCII), Planning Loop section (full conditional logic), State Management section, tool stubs in agent.py (TODO steps already marked)
- Expected output: A Python function that (1) parses user input, (2) calls search_listings with parsed params, (3) branches on empty results (sets session['error'] and returns), (4) calls suggest_outfit, (5) branches on empty wardrobe, (6) calls create_fit_card, (7) returns session dict
- Verification: (a) Run with example query — all three tools called, session dict populated; (b) Run with query that returns no results — only search_listings called, session['error'] set, fit_card remains None; (c) Print session after each step to verify state flows correctly

**handle_query() in app.py:**
- AI tool: Claude
- Input: run_agent() implementation, Gradio output structure (three text panels: search_result, outfit_suggestion, fit_card_text)
- Expected output: A Python function that (1) calls run_agent() with user input, (2) maps session dict to output strings (e.g., session['fit_card'] → fit_card_text output panel), (3) formats error messages for display
- Verification: Run through Gradio UI and check that outputs appear in the correct panels

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**User's wardrobe (provided earlier):**
```json
{
  "items": [
    {"id": "w_001", "name": "Baggy straight-leg jeans, dark wash", "category": "bottoms", "colors": ["dark blue", "indigo"], "style_tags": ["denim", "streetwear", "baggy"], "notes": "High-waisted"},
    {"id": "w_007", "name": "Chunky white sneakers", "category": "shoes", "colors": ["white"], "style_tags": ["sneakers", "chunky", "streetwear"], "notes": null}
  ]
}
```

**Step 1 — search_listings() call:**
- **Input:** `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`
- **Processing:** Function loads all 10 listings from listings.json, filters for items with "vintage", "graphic tee", or "band tee" in title/style_tags and price ≤ 30. Matches:
  - lst_002: "Y2K Baby Tee — Butterfly Print", $18, tops
  - lst_006: "Graphic Tee — 2003 Tour Bootleg Style", $24, tops
- **Output (returned):** List of 2 matching listings, sorted by keyword relevance (lst_006 first because it explicitly has "band tee" tag)
- **Session state after Step 1:** `session['selected_item'] = lst_006` (the top result)

**Step 2 — suggest_outfit() call:**
- **Input:** `suggest_outfit(new_item=session['selected_item'], wardrobe=user_wardrobe)` 
  - new_item = `{"id": "lst_006", "title": "Graphic Tee — 2003 Tour Bootleg Style", "colors": ["black"], "style_tags": ["graphic tee", "vintage", "grunge", "streetwear", "band tee"], ...}`
  - wardrobe = the user's 2 items (baggy jeans, chunky white sneakers)
- **LLM Prompt:** "The user found this item: [graphic tee details]. Their wardrobe includes: [baggy jeans, chunky white sneakers]. Suggest a specific outfit by naming which wardrobe items to pair with it and include styling tips."
- **LLM Response (example):** "Pair this faded band tee with your baggy dark wash jeans for an authentic 90s grunge vibe. The black graphic will contrast perfectly with the indigo denim. Leave the tee untucked for that relaxed fit, and wear it with your chunky white sneakers to ground the look with a fresh counterpoint. You've already got the baseline 90s aesthetic down — this tee is made for your wardrobe."
- **Session state after Step 2:** `session['outfit_suggestion'] = "Pair this faded band tee..."`

**Step 3 — create_fit_card() call:**
- **Input:** `create_fit_card(outfit=session['outfit_suggestion'], new_item=session['selected_item'])`
- **LLM Prompt:** "Write an Instagram/TikTok fit card caption for someone who just bought this item: [graphic tee, $24, Depop]. The outfit is: [the suggestion from step 2]. Use casual language, emoji, mention the platform and price, and hype it like a real thrifter would. Keep it under 280 characters."
- **LLM Response (example):** "thrifted this faded band tee off depop for $24 and honestly it was made for my baggy jeans 🖤 90s grunge era activated. full look in my stories"
- **Session state after Step 3:** `session['fit_card'] = "thrifted this faded band tee..."`

**Final output to user:**
The Gradio UI displays three panels:

1. **Search Results Panel:** "Found 2 listings for 'vintage graphic tee' under $30 — Top match: **Graphic Tee — 2003 Tour Bootleg Style** | $24 | Depop | Good condition"
2. **Outfit Suggestion Panel:** "Pair this faded band tee with your baggy dark wash jeans for an authentic 90s grunge vibe. The black graphic will contrast perfectly with the indigo denim. Leave the tee untucked for that relaxed fit, and wear it with your chunky white sneakers..."
3. **Fit Card Panel:** "thrifted this faded band tee off depop for $24 and honestly it was made for my baggy jeans 🖤 90s grunge era activated. full look in my stories"

The user can copy any of these outputs to share or save for reference.
