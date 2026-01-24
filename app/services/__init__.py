"""
Image retrieval services.

Workflow:
1. Pick random coordinates from the duckdb database, within specified location filters (e.g., country, admin1).
2. Retrieve closest street level view using Mapillary API.
3. Ensure there are enough plants in the vicinity using the database.
4. Repeat until the desired number of images is collected.
"""

