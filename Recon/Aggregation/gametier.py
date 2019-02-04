from Recon.Aggregation import players
from Recon.Utility import database as db
import datetime
import math

LAST_UPDATED_THRESHOLD = 7  # Days before player needs to update

# Checks tier for ranked game by examining 'average' player rank.
# Returns True if tier is at least Platinum
def gametier_calc(game_data, region):
    old_debug_all = db.Connection.debug_all
    db.Connection.debug_all = False
    player_keys = {}
    sum = 0
    total = 10
    masters = 0
    challengers = 0
    for each in game_data['participantIdentities']:
        conn = db.Connection()
        player_id = each['player']['summonerId']
        player = conn.player_get(player_id, region)
        conn.close()
        try:
            last_updated = datetime.datetime.now() - player[0]['lastUpdated']
            last_updated = last_updated.days
        except IndexError:
            last_updated = 999
        if len(player) == 0 or last_updated >= LAST_UPDATED_THRESHOLD:
            found = players.getRanksFromLeague(region, player_id)
            if not found:
                total -= 1
                continue
            else:
                conn = db.Connection()
                player = conn.player_get(player_id, region)
                conn.close()
                if len(player) == 0:
                    total -= 1
                    continue
        player = player[0]
        player_keys[player['summonerID']] = player['playerKey']
        tier = player['tier']
        div = player['division']
        if ((tier == 6) or (tier == 7)):
            div = 5
        sum += tier
        sum += 0.2 * (5 - div)

    mean = sum / total
    if challengers >= 5:
        tier_score = 7
    if masters >= 5:
        tier_score = 6
    else:
        if mean > 6.25:
            tier_score = 7
        elif mean > 6:
            tier_score = 6
        else:
            tier_score = math.floor(mean)
    db.Connection.debug_all = old_debug_all
    return tier_score, player_keys
