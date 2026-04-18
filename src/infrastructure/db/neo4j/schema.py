NODE_LABELS = {
    "COMPANY": "Company",
    "MANAGER": "Manager",
    "FORM": "Form",
    "SECTION": "Section",
    "CHUNK": "Chunk",
}

RELATIONSHIPS = {
    "SUBMITTED": "SUBMITTED",
    "CONTAINS": "CONTAINS",
    "STARTS_WITH": "STARTS_WITH",
    "NEXT": "NEXT",
    "BELONGS_TO": "BELONGS_TO",
    "INVESTED_IN": "INVESTED_IN",
}

SECTION_ITEMS = {
    "ITEM_1": "item1",
    "ITEM_1A": "item1a",
    "ITEM_7": "item7",
    "ITEM_7A": "item7a",
}

SECTION_NAMES = {
    "item1": "Business",
    "item1a": "Risk Factors",
    "item7": "Management's Discussion and Analysis (MD&A)",
    "item7a": "Quantitative and Qualitative Disclosures About Market Risk",
}

CONSTRAINTS = [
    ("Company", "cik"),
    ("Manager", "manager_cik"),
    ("Form", "form_id"),
    ("Section", "section_id"),
    ("Chunk", "chunk_id"),
]

INDEXES = {
    "vector": [
        ("Form", "text_embedding", 384),
        ("Section", "text_embedding", 384),
        ("Chunk", "text_embedding", 384),
    ],
    "btree": [
        ("Company", "name"),
        ("Company", "cusip6"),
        ("Form", "cik"),
        ("Form", "cusip6"),
        ("Section", "item"),
        ("Section", "form_id"),
        ("Chunk", "form_id"),
        ("Chunk", "item"),
        ("Chunk", "cik"),
        ("Manager", "name"),
    ]
}
