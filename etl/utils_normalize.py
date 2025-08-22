import re
from rapidfuzz import fuzz

SIZE_RE = re.compile(r'(\d{2,3})\s?ml', re.IGNORECASE)

CONC_MAP = {
    "eau de parfum": "EDP",
    "edp": "EDP",
    "eau de toilette": "EDT",
    "edt": "EDT",
    "parfum": "Parfum",
}

STOPWORDS = {"original", "authentic", "for men", "for women", "unisex"}

def normalize_title(title:str)->dict:
    t = title.lower()
    size_ml = None
    m = SIZE_RE.search(t)
    if m: size_ml = int(m.group(1))
    for k,v in CONC_MAP.items():
        t = t.replace(k, v.lower())
    for sw in STOPWORDS:
        t = t.replace(sw, "")
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return {"norm_title": t, "size_ml": size_ml}

def fuzzy_match_to_product(title:str, products)->str|None:
    """products is a pandas DataFrame with columns: product_id, brand, line, name, size_ml, concentration"""
    norm = normalize_title(title)
    best = (None, 0)
    for idx,row in products.iterrows():
        target = f"{row.brand} {row.line} {row.name} {row.size_ml}"
        score = fuzz.token_set_ratio(norm["norm_title"], target.lower())
        if score > best[1]:
            best = (row.product_id, score)
    return best[0] if best[1] >= 85 else None 
