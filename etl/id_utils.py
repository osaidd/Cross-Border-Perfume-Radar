import hashlib

def make_product_id(brand:str, line:str, name:str, size_ml:int, concentration:str)->str:
    key = f"{brand}|{line}|{name}|{size_ml}|{concentration}".lower().strip()
    return hashlib.sha1(key.encode()).hexdigest()[:12] 
