# NOTE – RFQ Parser

## Approach
Rule-based Python using only the standard library (`re`, `difflib`). One small function per field:
- **category**: keyword lists checked in a fixed order (fibc → mono_carton → bopp_bag → woven_sack → pouch → film → box). "BOPP film" is treated as film, not a bag. `difflib` fixes spelling mistakes (e.g. "corrugted").
- **quantity/unit**: find every number (handles `1,50,000`, `2.5 lac`, `15K`, `40 hazaar`, `ek lakh`), then throw away numbers that are gsm, micron, ply, size (12x10x8), days, price, or a fill weight/capacity ("25 kg bag", "1000 kg capacity"). Of the rest, the number with a count unit wins (weight wins for film).
- **gsm / micron**: simple regex next to "gsm" / "mic".
- **location**: known city list, then words after "to/at/in/delivery", then "X me/tak", then an unknown last word. So unseen cities still work.

## Score on my_tests.jsonl
56/56 exact match (every field correct). Caution: I wrote the tests myself and fixed bugs against them, so the real hidden-set score will be lower.

## 3 messages it gets wrong
1. `need stretch film 300 kg from Surat supplier, deliver to Pune` → location "Surat" (should be Pune). The known-city step takes the first city, not the delivery one.
2. `1 container jumbo bags Chennai` → quantity 1, unit pcs. "Container" is not a unit I handle.
3. `bags chaiye 3 lakh 60 gsm raipur chattisgarh` → "Raipur"; a state name is not a city, and I have no rule for choosing between two places.

## With 1,000 real labelled examples
Measure errors per field, then fix the most common ones. Replace the hand-made city list with places taken from the data, and possibly train a small model (e.g. spaCy NER or a fine-tuned small transformer) only for location and category, keeping the rules for numbers.

## How I would know it works with real buyers
Log every parsed message. Sample ~50 per week and check by hand. Track how often fields come back empty and how often the matched supplier/ buyer corrects a field. Alert if the empty-field rate jumps.

## Tools used
I used Claude (AI assistant) to draft parse.py and the test examples. I read the code, ran the tests, and understand each function; [EDIT THIS: write what you personally changed or checked].
