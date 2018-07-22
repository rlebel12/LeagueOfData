from Recon.Utility import core
from Recon.Utility import database as db

# Used for the counting option listed below
def count():
    conn = db.Connection()

    results = conn.execute('''SELECT COUNT(*) AS 'count' FROM Player''')
    results = str(results[0]['count'])
    print("Number of players being tracked: " + results)

    results = conn.execute('''SELECT COUNT(*) AS 'count' FROM Game''')
    results = str(results[0]['count'])
    print("Number of matches stored (total): " + results)

    results = conn.execute('''SELECT COUNT(*) AS 'count' FROM Game
                            WHERE patchMajor = %s AND patchMinor = %s''',
                           (core.PATCH_MAJOR, core.PATCH_MINOR))
    results = str(results[0]['count'])
    print("Number of matches stored (current patch): " + results)
    del conn
