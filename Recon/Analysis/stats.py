"""
This module is responsible for the data aggregation
component of the application.
"""

from Recon.Aggregation import collect
from Recon.Utility import core
from Recon.Utility import database as db
import random
import multiprocessing
import threading
import json
import datetime

# TODO: Skip checking existing matches when collecting, rely on integrity
#       errors

changeTeam = {100: 0, 200: 1}
changeWin = {"Win": 1, "Fail": 0, "True": 1, "False": 0,
             bool(0): 0, bool(1): 1}
wantedStatKeys = [
    'kills', 'deaths', 'assists', 'largestMultiKill',
    'largestKillingSpree',
    'totalTimeCrowdControlDealt', 'totalMinionsKilled', 'neutralMinionsKilled',
    'neutralMinionsKilledTeamJungle', 'neutralMinionsKilledEnemyJungle',
    'totalDamageDealtToChampions', 'goldEarned',
    'totalHeal', 'totalDamageTaken', 'turretKills']
# THIS ORDER MATTERS, MUST MATCH THE QUERY!!!


# Inserts stats into champion winrate table,
# taking dictionary containing list of wanted stats
def champ_stats_add(stats):
    print("Adding stats...")
    #print(stats)
    key = stats['matchKey']
    lane = stats['lane']
    dur = stats['duration']
    win = stats['win']
    playerKey = stats['playerKey']
    champId = stats['champId']
    statSummary = stats['statSummary']
    conn = db.Connection()
    conn.champ_stats_save(key, champId, playerKey, lane, dur, win, statSummary)
    del conn
    #conn.__del__()

# For a list of matches, retrieves data for each match (either from my DB
# or using Riot API).  After retrieving data, parses out information
# to be used to track champion winrates.
def match_stats_add(matches, region):
    for each in matches:
        id = each
        #print(matches.index(id))
        matchData, tier, key, playerKeys = collect.match_data_get(id, region)
        if matchData == -2:
            print("Returning to collect more matches...")
            del matches
            return
        if matchData == -1:
            continue
        else:
            dur = matchData['gameDuration']
            for i in range(len(matchData['participants'])):
                try:
                    statSummary = []
                    participantData = matchData['participants'][i]
                    champId = participantData['championId']
                    win = changeWin[participantData['stats']['win']]
                    participantID = participantData['participantId']
                    for each1 in matchData['participantIdentities']:
                        if each1['participantId'] == participantID:
                            playerID = each1['player']['summonerId']
                            break
                    playerKey = playerKeys[playerID]
                    lane = participantData['timeline']['lane']
                    if lane == "BOTTOM":
                        role = participantData['timeline']['role']
                        if role == "DUO_SUPPORT":
                            lane = "SUPPORT"
                        else:
                            lane = "BOT"

                    # For stat summary
                    '''statSummary = {}
                    originalStats = participantData['stats']
                    for statKey in originalStats:
                        if statKey not in wantedStatKeys:
                            continue
                        statSummary[statKey] = originalStats[statKey]'''
                    originalStats = participantData['stats']
                    for each in wantedStatKeys:
                        try:
                            statSummary.append(originalStats[each])
                        except:
                            print("KEY NOT FOUND: " + each)
                            raise "Error finding key"
                    # mastery = getChampMasteryCRS(
                    #   crs,playerID,region,
                    #   matchData['participants'][i]['championId'])
                    stats = {'matchKey': key, 'champion': champId, 'duration': dur,
                             'win': win, 'lane': lane, 'playerKey': playerKey,
                             'champId': champId, 'statSummary': statSummary}
                    champ_stats_add(stats)
                except:
                    statSummary.append(None)
                    continue


# Worker function for new threads (see below function)
def matchesToTrackerWorker(matchList, region):
    conn = db.Connection()
    newMatches = []
    for each in matchList:
        full = conn.champ_stats_full(each['gameKey'])
        if not full:
            newMatches.append(each['gameID'])
    del conn
    match_stats_add(newMatches, region)


# Used to parse data from collected matches that have not been added to
# champion winrate table
def matchesToTracker(region):
    conn = db.Connection()
    response = conn.matches_elite_get(region)
    del conn
    #conn.__del__()
    matchesToTrackerWorker(response, region)
    core.sys.exit()  # TODO delete this and above line
    arrs = core.threader(6, response)
    threads = []
    for each in arrs:
        t = threading.Thread(target=matchesToTrackerWorker,
                               args=(each, region))
        t.daemon = True
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    # print("Done filling tracker.")
