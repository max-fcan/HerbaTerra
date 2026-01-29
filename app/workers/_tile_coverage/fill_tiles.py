import duckdb
import mercantile

DB = "data/gbif_plants.duckdb"
Z = 14

con = duckdb.connect(DB)

rows = con.execute("SELECT rowid, lat, lon FROM images WHERE lat IS NOT NULL AND lon IS NOT NULL").fetchall()

# updates = []
# for rowid, lat, lon in rows:
#     t = mercantile.tile(lon, lat, Z)
#     updates.append((Z, t.x, t.y, rowid))

# con.executemany("UPDATE images SET tile_z=?, tile_x=?, tile_y=? WHERE rowid=?", updates)
# print(f"updated {len(updates)} rows")

# Or execute in batches
BATCH_SIZE = 1000
for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i : i + BATCH_SIZE]
    updates = []
    for rowid, lat, lon in batch:
        t = mercantile.tile(lon, lat, Z)
        updates.append((Z, t.x, t.y, rowid))
    con.executemany("UPDATE images SET tile_z=?, tile_x=?, tile_y=? WHERE rowid=?", updates)
    print(f"updated {len(updates)} rows in batch {i // BATCH_SIZE + 1}")