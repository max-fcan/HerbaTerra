"""
HerbaTerra service layer.

Modules:
    db          – DuckDB connection management (connect / get_persistent)
    catalogue   – Species catalogue queries (autocomplete, pagination, filters, detail)
    challenge   – Random plant-image selection for the guessing game
    mapillary   – Mapillary Graph API client with retry logic
    geocoding   – Reverse geocoding and continent tagging
"""

