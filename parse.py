"""
parse.py - Rule-based RFQ parser for Kypson Solutions.

No external libraries (only Python's standard library), so it is fast and
easy to explain. Each field has its own small function:

    find_category()  -> which packaging product
    find_quantity()  -> how many units to order (and the unit)
    find_gsm()       -> GSM number
    find_micron()    -> thickness in microns
    find_location()  -> delivery city / country

Main entry point: parse_rfq(text)
"""
import re
from difflib import get_close_matches


# =====================================================================
# 1. CATEGORY
# =====================================================================
# Words are matched at the START of a word, so "box" also matches "boxes".
FIBC_WORDS = ["fibc", "jumbo", "bulk bag", "big bag", "super sack"]
MONO_WORDS = ["mono", "folding carton"]
BOPP_WORDS = ["bopp", "bop", "laminated"]

# Checked in this order AFTER fibc / mono_carton / bopp_bag.
OTHER_CATEGORIES = [
    ("woven_sack", ["woven", "cement bag", "ad star", "adstar", "pp bag",
                    "hdpe", "sack", "bori", "bora", "raffia"]),
    ("pouch", ["pouch", "sachet", "stand up", "standup", "zipper",
               "doypack", "pauch"]),
    ("film", ["film", "shrink", "stretch", "wrap", "cling"]),
    ("corrugated_box", ["corrugated", "box", "carton", "cartoon",
                        "dabba", "dibba"]),
]

# Used only when nothing matched exactly (to fix spelling mistakes).
FUZZY_WORDS = {
    "fibc": "fibc", "jumbo": "fibc",
    "mono": "mono_carton",
    "bopp": "bopp_bag",
    "woven": "woven_sack", "sack": "woven_sack",
    "pouch": "pouch", "sachet": "pouch",
    "film": "film", "shrink": "film", "stretch": "film",
    "corrugated": "corrugated_box", "carton": "corrugated_box",
}


def has(text, words):
    """True if any of the words/phrases starts a word somewhere in text."""
    return any(re.search(r"\b" + re.escape(w), text) for w in words)


def find_category(t):
    """t is the lowercase message."""
    if has(t, FIBC_WORDS):
        return "fibc"
    if has(t, MONO_WORDS):
        return "mono_carton"

    if has(t, BOPP_WORDS):
        # "BOPP film" or "laminated pouch" are NOT bags
        is_bag = has(t, ["bag", "sack", "bori", "woven"])
        if has(t, ["film"]) and not is_bag:
            return "film"
        if has(t, ["pouch"]) and not is_bag:
            return "pouch"
        return "bopp_bag"

    for category, words in OTHER_CATEGORIES:
        if has(t, words):
            return category

    # Spelling mistakes: compare each word with our keywords
    for word in re.findall(r"[a-z]+", t):
        if len(word) >= 4:
            close = get_close_matches(word, FUZZY_WORDS.keys(), n=1, cutoff=0.8)
            if close:
                return FUZZY_WORDS[close[0]]

    # Just "bag" with nothing else -> most common type
    if has(t, ["bag", "thaila", "thaili"]):
        return "woven_sack"
    return None


# =====================================================================
# 2. QUANTITY + UNIT
# =====================================================================
MULTIPLIERS = {
    "k": 1000, "thousand": 1000, "hazaar": 1000, "hazar": 1000,
    "hajar": 1000, "hajaar": 1000,
    "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000,
    "crore": 10000000, "million": 1000000,
}

# Hindi / English number words that can come before lakh / hazaar
WORD_NUMBERS = {
    "ek": 1, "one": 1, "do": 2, "two": 2, "teen": 3, "three": 3,
    "char": 4, "four": 4, "paanch": 5, "panch": 5, "five": 5,
    "chhe": 6, "six": 6, "saat": 7, "seven": 7, "aath": 8, "eight": 8,
    "nau": 9, "nine": 9, "das": 10, "ten": 10, "pachas": 50, "fifty": 50,
    "dedh": 1.5, "dhai": 2.5,
}

# number  +  optional multiplier   e.g.  "1,50,000"  "2.5 lac"  "15k"  "40 hazaar"
NUMBER_RE = re.compile(
    r"(\d+(?:,\d+)*(?:\.\d+)?)"
    r"(?:\s*(k|thousand|hazaar|hazar|hajar|hajaar|lakhs|lakh|lacs|lac|crore|million)(?![a-z]))?"
)
# sizes like 12x10x8 (these numbers are NOT the quantity)
DIMENSION_RE = re.compile(r"\d+(?:\.\d+)?(?:\s*[x×*]\s*\d+(?:\.\d+)?)+")

KG_UNITS = {"kg", "kgs", "kilo", "kilos", "kilogram", "kilograms"}
MT_UNITS = {"mt", "mts", "ton", "tons", "tonne", "tonnes", "tonn"}
COUNT_UNITS = {
    "pcs", "pc", "pce", "piece", "pieces", "nos", "no", "unit", "units",
    "number", "numbers", "bag", "bags", "sack", "sacks", "box", "boxes",
    "carton", "cartons", "pouch", "pouches", "roll", "rolls", "set", "sets",
    "packet", "packets", "bori", "thaila", "thaile", "dabba", "dabbe",
}
# A number followed by one of these is NOT a quantity
# (gsm, micron, size, plies, colours, grams, metres, days, money ...)
SKIP_UNITS = {
    "gsm", "gms", "gsn", "mm", "cm", "inch", "inches", "ply", "layer",
    "layers", "color", "colour", "colors", "colours", "ml", "ltr", "ltrs",
    "litre", "liter", "litres", "gm", "gram", "grams", "g", "mtr", "mtrs",
    "meter", "metre", "meters", "metres", "feet", "ft", "day", "days", "din",
    "week", "weeks", "hafte", "month", "months", "mahine", "year", "years",
    "saal", "hrs", "hours", "th", "st", "nd", "rd", "rs", "rupees", "inr",
    "percent", "%", "micron", "microns",
}
# A number right AFTER one of these words is NOT a quantity
SKIP_BEFORE = {
    "gsm", "mic", "micron", "thickness", "size", "ply", "rs", "inr", "price",
    "rate", "budget", "per", "width", "length", "height", "dia", "pin",
    "pincode", "phone", "mobile", "mob", "contact", "call", "whatsapp",
}
# kg / ton that describe ONE bag (fill weight / capacity), not the order size
FILL_PREV = {"capacity", "cap", "of", "upto", "holding", "load", "loading",
             "carrying", "each"}
FILL_NEXT = {"capacity", "cap", "load", "wali", "wala", "wale", "each",
             "bag", "bags", "sack", "sacks", "pouch", "pouches", "box",
             "boxes", "carton", "cartons", "bori", "thaila", "thaili"}


def replace_number_words(t):
    """'ek lakh' -> '1 lakh',  'das hazaar' -> '10 hazaar'"""
    pattern = (r"\b(" + "|".join(WORD_NUMBERS) + r")\s+"
               r"(hazaar|hazar|hajar|hajaar|thousand|lakhs|lakh|lacs|lac|crore|million)\b")
    return re.sub(pattern, lambda m: f"{WORD_NUMBERS[m.group(1)]} {m.group(2)}", t)


def find_quantity(t, category):
    """Returns (quantity, unit). (None, None) if nothing found."""
    t = replace_number_words(t)
    t = DIMENSION_RE.sub(" dims ", t)

    candidates = []  # each: (priority, position, value, unit) - lowest priority wins

    for m in NUMBER_RE.finditer(t):
        digits = m.group(1)
        value = float(digits.replace(",", ""))
        multiplier = m.group(2)
        if multiplier:
            value *= MULTIPLIERS[multiplier]

        # words just before / after the number, inside the same comma-part
        before = re.split(r"[,;\n]", t[:m.start()])[-1]
        after = re.split(r"[,;\n]", t[m.end():])[0].lstrip(" -")
        prev_words = re.findall(r"[a-z]+", before)
        prev = prev_words[-1] if prev_words else ""
        unit_match = re.match(r"[a-z]+|%", after)
        unit_word = unit_match.group(0) if unit_match else ""
        next_words = re.findall(r"[a-z]+", after)[1:4]

        # ---- rules to throw this number away ----
        if unit_word in SKIP_UNITS or unit_word.startswith("mic"):
            continue
        # "gsm 65", "micron 25", "rs 12" -> skip, unless a real unit follows
        # (e.g. "20 micron 400 kg": the 400 kg is fine)
        has_real_unit = (unit_word in KG_UNITS or unit_word in MT_UNITS
                         or unit_word in COUNT_UNITS)
        if prev in SKIP_BEFORE and not has_real_unit:
            continue

        if unit_word in KG_UNITS or unit_word in MT_UNITS:
            # "25 kg bag", "1000 kg capacity", "bags of 25 kg" -> not the order size
            if prev in FILL_PREV or any(w in FILL_NEXT for w in next_words):
                continue
            unit = "kg" if unit_word in KG_UNITS else "mt"
            # film is sold by weight, so weight is most likely the quantity
            priority = 1 if category == "film" else 3
        elif unit_word in COUNT_UNITS:
            unit = "pcs"
            priority = 2 if category == "film" else 1
        else:
            # plain number such as "5000 bopp bags" or "1 lakh"
            whole = digits.split(".")[0].replace(",", "")
            # long number that is not round = phone number / pincode
            if not multiplier and len(whole) >= 6 and not whole.endswith("00"):
                continue
            unit = "pcs"
            priority = 3 if category == "film" else 2

        candidates.append((priority, m.start(), value, unit))

    if not candidates:
        return None, None

    _, _, value, unit = min(candidates)
    value = round(value, 2)
    if value == int(value):
        value = int(value)
    return value, unit


# =====================================================================
# 3. GSM and MICRON
# =====================================================================
def find_gsm(t):
    m = (re.search(r"(\d+(?:\.\d+)?)\s*(?:gsm|gms|gsn)\b", t)
         or re.search(r"\b(?:gsm|gms)\s*[:=\-]?\s*(\d+(?:\.\d+)?)", t))
    return int(float(m.group(1))) if m else None


def find_micron(t):
    m = (re.search(r"(\d+(?:\.\d+)?)\s*(?:mic\w*|μ|µ)", t)
         or re.search(r"\b(?:mic\w*|thickness)\s*[:=\-]?\s*(\d+(?:\.\d+)?)", t))
    return int(float(m.group(1))) if m else None


# =====================================================================
# 4. LOCATION
# =====================================================================
# Common places (a helper only - unknown places are found by the rules below)
PLACES = """mumbai delhi new delhi bangalore bengaluru hyderabad ahmedabad chennai kolkata
pune surat jaipur lucknow kanpur nagpur indore bhopal visakhapatnam patna
vadodara ghaziabad ludhiana agra nashik faridabad meerut rajkot varanasi
srinagar aurangabad dhanbad amritsar allahabad prayagraj ranchi howrah
coimbatore jabalpur gwalior vijayawada jodhpur madurai raipur kota
chandigarh guwahati solapur hubli mysore mysuru tiruchirappalli bareilly
thiruvananthapuram bhubaneswar salem warangal guntur noida gurgaon gurugram
navi mumbai thane vasai kochi cochin kozhikode thrissur goa udaipur ajmer
bikaner bhilai bilaspur dehradun haridwar jammu ambala panipat sonipat
rohtak bhiwandi kandla gandhidham morbi jamnagar bhavnagar gandhinagar
vapi daman silvassa pithampur baddi sangli kolhapur nanded akola amravati
dubai abu dhabi sharjah uae oman qatar kuwait saudi arabia bahrain nepal
bangladesh sri lanka bhutan pakistan afghanistan singapore malaysia
indonesia thailand vietnam kenya nigeria ghana tanzania egypt ethiopia
south africa uk usa germany france italy australia canada india
""".split("\n")
# the text above is written one-line-per-group; split into single words,
# then rebuild the 2-word names we care about
_words = " ".join(PLACES).split()
PLACE_LIST = set(_words)
for two in ["new delhi", "navi mumbai", "abu dhabi", "saudi arabia",
            "sri lanka", "south africa"]:
    PLACE_LIST.add(two)
# remove the halves of 2-word names so "new" or "abu" alone is not a place
for half in ["new", "navi", "abu", "dhabi", "saudi", "arabia", "sri", "lanka",
             "south", "africa"]:
    PLACE_LIST.discard(half)
PLACE_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, PLACE_LIST), key=len, reverse=True)) + r")\b"
)

# Words that are NEVER a place name
STOP = set("""
a an the and or of for from on by with without is are am was be to at in per me my our we i you your
hello hi hii hey dear sir madam bhai bhaiya ji please pls plz kindly thanks thank regards
need needed want wanted require required requirement requirements looking buy purchase order send share give
quote quotation price rate rates cost best good quality new regular urgent urgently asap immediately sample samples
chahiye chahie chaiye chahiyega hai hain ka ki ke ko se aur ya bhi wala wale wali bhejo bhej dena dijiye kijiye
karo mujhe humko hume hamein hame mera meri jaldi abhi bhav bhaav kitna kya kab nahi mein mai tak pe par liye
supplier suppliers manufacturer manufacturers wholesale dealer vendor contact call whatsapp
delivery deliver delivered location dispatch ship shipping near destination
bulk white red blue black yellow green color colour colors colours transparent plain printed print printing
size thickness capacity cap load total approx approximately around about min max minimum maximum moq only also
stock ready each piece
pcs pc pieces nos no unit units number numbers kg kgs kilo mt mts ton tons tonne tonnes
gsm gms mic micron microns mm cm inch inches ply layer layers ml ltr litre rs rupees inr gm gram
roll rolls set sets pack packs packet packets dims
bag bags sack sacks box boxes carton cartons pouch pouches film films wrap shrink stretch woven bopp bop
laminated jumbo fibc mono folding corrugated cement ad star adstar pp hdpe bori bora thaila dabba raffia
sachet stand up zipper
k thousand hazaar hazar hajar lakh lakhs lac lacs crore million
ek do teen char paanch panch chhe saat aath nau das ten one two three four five six seven eight nine dedh dhai
days day week weeks month months monthly weekly din hafte mahine within
""".split())
STOP_LIST = sorted(STOP)

# "deliver to X", "in X", "at X" ...  -> X is the place
BEFORE_MARKERS = {"in", "at", "to", "deliver", "delivery", "delivered", "location",
                  "dispatch", "ship", "shipping", "near", "destination"}
# words that may sit between the marker and the place: "delivery to X"
FILLER_AFTER_MARKER = {"to", "at", "in", "location", "is", "of", "the", "for"}
# "X me", "X tak" (Hindi) -> X is the place
AFTER_MARKERS = {"me", "mein", "mai", "tak", "pe", "par"}


def pretty(place):
    special = {"uae": "UAE", "usa": "USA", "uk": "UK"}
    return " ".join(special.get(w, w.capitalize()) for w in place.split())


def looks_like_place(word):
    """Not a number, not a known normal word, not a misspelling of one."""
    if not word.isalpha() or len(word) < 3 or word in STOP:
        return False
    return not get_close_matches(word, STOP_LIST, n=1, cutoff=0.85)


def find_location(text):
    t = text.lower()
    tokens = re.findall(r"[a-z]+|\d+", t)

    # Step 1: a well-known city / country
    m = PLACE_RE.search(t)
    if m:
        return pretty(m.group(0))

    # Step 2: word(s) after "to / at / in / delivery ..."
    for i, word in enumerate(tokens):
        if word in BEFORE_MARKERS:
            j = i + 1
            while j < len(tokens) and tokens[j] in FILLER_AFTER_MARKER:
                j += 1
            place = []
            while (j < len(tokens) and len(place) < 2
                   and tokens[j].isalpha() and tokens[j] not in STOP):
                place.append(tokens[j])
                j += 1
            if place:
                return pretty(" ".join(place))

    # Step 3: word before "me / mein / tak"  (Hindi style: "Pune me chahiye")
    for i, word in enumerate(tokens):
        if word in AFTER_MARKERS and i > 0 and looks_like_place(tokens[i - 1]):
            return pretty(tokens[i - 1])

    # Step 4: last comma-part is just 1-2 unknown words  (", Bhilwara")
    last_part = re.split(r"[,;\n]", t)[-1]
    words = re.findall(r"[a-z]+", last_part)
    if 1 <= len(words) <= 2 and all(looks_like_place(w) for w in words) \
            and not re.search(r"\d", last_part):
        return pretty(" ".join(words))

    # Step 5: the very last word of the message is an unknown word
    if tokens and looks_like_place(tokens[-1]):
        return pretty(tokens[-1])

    return None


# =====================================================================
# MAIN FUNCTION
# =====================================================================
def parse_rfq(text: str) -> dict:
    t = (text or "").lower()
    category = find_category(t)
    quantity, unit = find_quantity(t, category)
    return {
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "gsm": find_gsm(t),
        "micron": find_micron(t),
        "location": find_location(text or ""),
    }


if __name__ == "__main__":
    for msg in ["bopp bags chahiye 40 hazaar, 65 gsm, Nagpur",
                "jumbo bag 1000 kg capacity, 500 pcs, Vadodara",
                "need quote for 500 kg shrink wrap 25 mic"]:
        print(msg, "->", parse_rfq(msg))
