import re

def custom_slugify(text):
    if not text:
        return ""

    text = text.lower()

    text = text.replace("https://", "").replace("http://", "").replace("www.", "")

    tr_map = {
        'ş': 's', 'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
        'Ş': 's', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ö': 'o', 'Ç': 'c', 'İ': 'i'
    }
    for tr_char, en_char in tr_map.items():
        text = text.replace(tr_char, en_char)

    text = re.sub(r'[^a-z0-9]+', '-', text)

    text = text.strip('-')

    return text