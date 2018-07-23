"""
This module is responsible for the data aggregation
component of the application.
"""

from Recon.Analysis import stats
from Recon.Aggregation import gametier
from Recon.Utility import core
from Recon.Utility import database as db
import random
import multiprocessing
import threading
import json
import datetime
import sys

# TODO: Skip checking existing matches when collecting, rely on integrity
#       errors


# Retrieves stats for every player from given match, and returns stats
def match_data_get(id, region):
    conn = db.Connection()
    matchInfo = conn.match_info_get(id, region)
    del conn
    if len(matchInfo) == 0:
        print("Match data for " + str(id) + " does not exist.  "
              "Adding to database...")
        url = ("https://" + region.lower() +
               ".api.riotgames.com/lol/match/v3/matches/" + str(id))
        try:
            response = core.api_get(url).json()
            data = json.dumps(response)
            tier, players = gametier.gametier_calc(response, region)
            version = response['gameVersion'].split('.')
            patchMajor = int(version[0])
            patchMinor = int(version[1])
            if (patchMajor != core.PATCH_MAJOR or
                    patchMinor != core.PATCH_MINOR):
                    print("Game is not on current patch...")
                    conn = db.Connection()
                    conn.match_save(id, tier,
                                   patchMajor, patchMinor, region, None)
                    del conn
                    return -2, -2, -2, -2
            conn = db.Connection()
            key = conn.match_save(id, tier, patchMajor, patchMinor, region, data)
            del conn
            return response, tier, key, players
        except AttributeError as e:
            print("AttributeError")
            print(e)
            return -1, -1, -1, -1
    else:
        # TODO update this section to pull in playerKeys
        print("Match data for " + str(id) + " already exists.  Loading...")
        tier = matchInfo['rank']
        key = matchInfo['gameKey']
        conn = db.Connection()
        if not conn.champ_stats_full(key):
            data = conn.match_data_get(key)
            return data, tier, key
        else:
            print("Fully added data, no need for pull matchData.")
            data = tier = key = -1
        del conn
        return data, tier, key


# Collects entire list of matches for given summoner,
# starting from time defined in Header.py
def matches_collect(player, region, newMatches,
                   beginT=None, endT=None, recordStreak=0):
    if newMatches is None:
        newMatches = []
    if endT is None:
        epoch = datetime.datetime.utcfromtimestamp(0)
        now = datetime.datetime.now()
        now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        endT = int((now - epoch).total_seconds() * 1000)
        beginT = endT - 604800000
    accountID = player['accountID']
    url = ("https://" + region.lower() +
           ".api.riotgames.com/lol/match/v3/matchlists/by-account/" +
           str(accountID) + "?queue=420&beginTime=" + str(beginT) +
           "&endTime=" + str(endT))
    try:
        response = core.api_get(url).json()
        totalGames = response['totalGames']
        if totalGames == 0:
            return newMatches
        conn = db.Connection()
        for i in range(len(response['matches'])):
            if recordStreak == 20:
                print("20 recorded in a row.  Assuming done...")
                return newMatches
            game = response['matches'][i]
            if (game['queue'] != 420 or
               game['season'] != core.CURRENT_SEASON):
                continue
            else:
                '''print("Checking if match " +
                      str(game['gameId']) + " already recorded.")'''
                patchMajor, patchMinor = conn.match_exists(
                    str(game['gameId']), region)
                if patchMajor is not -1:
                    print("Data already recorded.")
                    if ((patchMajor != core.PATCH_MAJOR) or
                       (patchMinor != core.PATCH_MINOR)):
                        print("No longer on current patch...")
                        return newMatches
                    recordStreak += 1
                else:
                    '''print("Adding match " + str(game['gameId']) +
                          " to list of new matches.")'''
                    newMatches.append(game['gameId'])
        del conn
        newMatches = matches_collect(player, region, newMatches,
                                    beginT - 604800000,
                                    beginT, recordStreak)
        return newMatches
    except KeyError:  # Encountered if no matches found (404)
        return newMatches


def processWorker(region, summList, add_stats=True):
    shuffle = False
    while True:
        try:
            if shuffle:
                random.shuffle(summList)
            for each in summList:
                print("\nCollecting new matches for " + str(each['playerID']) + "...")
                newMatches = matches_collect(each, region, None)
                if add_stats:
                    print("\nAdding stats for new matches...\n")
                    stats.match_stats_add(newMatches, region)
                sys.stdout.flush()
        except Exception as e:
            print(e)
            print("Error encountered. Starting again.")
        shuffle = True


# Start of data aggregation function.  Gets list of high-rank summoners, and
# feeds portions of the list to separatred processes
def main(region):
    conn = db.Connection()
    summList = conn.players_elite_get(region)
    del conn
    procs = []
    arrs = core.threader(1, summList)
    for grouping in arrs:
        p = multiprocessing.Process(target=processWorker,
                                      args=(region, grouping,))
        procs.append(p)
        p.start()
    try:
        for each in procs:
            p.join()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
