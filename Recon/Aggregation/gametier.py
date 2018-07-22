from Recon.Aggregation import interfaceAPI
from Recon.Utility import database as db
import datetime
import math

LAST_UPDATED_THRESHOLD = 7  # Days before player needs to update


# Checks tier for ranked game by examining 'average' player rank.
# Returns True if tier is at least Platinum
def gametier_calc(matchData, region):
    playerKeys = {}
    avg = 0
    tot = 10
    masters = 0
    challengers = 0
    for each in matchData['participantIdentities']:
        conn = db.Connection()
        playerID = each['player']['summonerId']
        player = conn.getSumm(playerID, region)
        del conn
        #conn.__del__()
        try:
            daysSince = datetime.datetime.now() - player[0]['lastUpdated']
            daysSince = daysSince.days
        except IndexError:
            daysSince = 999
        if len(player) == 0 or daysSince >= LAST_UPDATED_THRESHOLD:
            found = interfaceAPI.getRanksFromLeague(region, playerID)
            if found == -1:
                tot -= 1
                continue
            else:
                conn = db.Connection()
                player = conn.getSumm(playerID, region)
                del conn
                #conn.__del__()
                if len(player) == 0:
                    tot -= 1
                    continue
        player = player[0]
        playerKeys[player['summonerID']] = player['playerKey']
        tier = player['tier']
        div = player['division']
        if ((tier == 6) or (tier == 7)):
            div = 5
        avg += tier
        avg += 0.2 * (5 - div)

    avg = avg / tot
    if challengers >= 5:
        tierScore = 7
    if masters >= 5:
        tierScore = 6
    else:
        if avg > 6.25:  # Somewhat arbitrary average
            tierScore = 7
        elif avg > 6:  # Somewhat arbitrary average
            tierScore = 6
        else:
            tierScore = math.floor(avg)
    return tierScore, playerKeys
