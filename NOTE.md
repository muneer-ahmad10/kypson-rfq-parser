# NOTE – RFQ Parser

## Approach
Rule-based Python using only the standard library (`re`, `difflib`), so `requirements.txt` is empty. I chose rules because there is no training data and every decision can be explained and changed quickly. One small function per field:
- **category**: keyword lists checked in a fixed order (fibc → mono_carton → bopp_bag → woven_sack → pouch → film → box). "BOPP film" is film, not a bag. `difflib` fixes spelling mistakes (e.g. "corrugted").
- **quantity/unit**: find every number (`1,50,000`, `2.5 lac`, `15K`, `40 hazaar`, `ek lakh`), then discard numbers that are gsm, micron, ply, size (12x10x8), days, price, or a fill weight/capacity ("25 kg bag", "1000 kg capacity"). Of the rest, a count (pcs) wins; for film, weight wins.
- **gsm / micron**: regex next to "gsm" / "mic".
- **location**: known city list first, then words after "to/at/in/delivery", then "X me/tak", then an unknown last word. So cities not in my list can still be found.

## Score on my_tests.jsonl
`python score.py my_tests.jsonl` → **56/56 (100%)** on every field, in 0.01 s.
Caution: I wrote these 56 tests myself and fixed bugs against them, so the score on your unseen set will be lower. I also tried about 20 extra messages written in a different style; most were right, and the wrong ones are listed below.

## 3 messages it gets wrong
1. `need stretch film 300 kg from Surat supplier, deliver to Pune` → location "Surat" (should be Pune). The known-city step takes the first city it sees, not the delivery city.
2. `1 container jumbo bags Chennai` → quantity 1, unit pcs. "Container" is not a unit I handle.
3. `bopp bags 5000 pcs 70 gsm regards Ravi` → location "Ravi". My last-word rule treats any unknown final word as a place, so a signature name is read as a city.

## With 1,000 real labelled examples
Count errors per field and fix the most common ones first. Build the city list from the real data instead of by hand, and learn which words signal a delivery city. Possibly add a small model (e.g. spaCy NER) for location and category only, keeping the rules for numbers, since rules work well there.

## How I would know it works with real buyers
Log every parsed message and check about 50 a week by hand. Track how often fields come back empty and how often a buyer or supplier corrects a field. Raise an alert if the empty-field rate suddenly jumps.

## Tools used
I used Claude (AI assistant) to draft parse.py, my_tests.jsonl and this note.
I read each function, ran everything in a virtual environment, ran score.py, and wrote and tried my own extra messages to find weaknesses.