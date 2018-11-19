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


# Retrieves stats for every player from given match, and returns stats
def game_data_get(key, region):
    print("test")
    conn = db.Connection()
    game_info = conn.game_info_get(key, region)
    conn.close()
    if len(game_info) == 0:
        print("Match data for " + str(key) + " does not exist.  "
              "Adding to database...")
        url = ("https://" + region.lower() +
               ".api.riotgames.com/lol/match/v3/matches/" + str(key))
        try:
            response = core.api_get(url).json()
            game_data = json.dumps(response)
            tier, players = gametier.gametier_calc(response, region)
            version = response['gameVersion'].split('.')
            patch_major = int(version[0])
            patch_minor = int(version[1])
            if (patch_major < core.PATCH_MAJOR or
                    patch_minor < core.PATCH_MINOR):
                    print("Game is not on current patch...")
                    conn = db.Connection()
                    conn.game_save(key, tier,
                                patch_major, patch_minor, region, game_data)
                    conn.close()
                    return -2, -2, -2, -2
            conn = db.Connection()
            key = conn.game_save(key, tier, patch_major, patch_minor, region, game_data)
            conn.close()
            return response, tier, key, players
        except AttributeError as e:
            print("AttributeError")
            print(e)
            return -1, -1, -1, -1
    else:
        # This section reached if data stored in 'Game' table
        # TODO update this section to pull in playerKeys
        print("Match data for " + str(key) + " already exists.  Loading...")
        tier = game_info[0]['rank']
        key = game_info[0]['gameKey']
        conn = db.Connection()
        if not conn.champ_stats_full(key):
            game_data = conn.game_data_get(key)
            return game_data, tier, key
        else:
            print("Fully added data, no need for pull matchData.")
            game_data = tier = key = -1
        conn.close()
        return game_data, tier, key


# Collects entire list of matches for given summoner,
# starting from time defined in Header.py
def games_collect(player, region, new_games,
                   time_begin=None, time_end=None, streak=0):
    if new_games is None:
        new_games = []
    if time_end is None:
        time_epoch = datetime.datetime.utcfromtimestamp(0)
        time_now = datetime.datetime.now()
        #time_now = time_now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_end = int((time_now - time_epoch).total_seconds() * 1000)
        time_begin = time_end - 604800000
    account_id = player['accountID']
    url = ("https://" + region.lower() +
           ".api.riotgames.com/lol/match/v3/matchlists/by-account/" +
           str(account_id) + "?queue=420&beginTime=" + str(time_begin) +
           "&endTime=" + str(time_end))
    try:
        game_history = core.api_get(url).json()
        total_games = game_history['totalGames']
        if total_games == 0:
            return new_games
        conn = db.Connection()
        for i in range(len(game_history['matches'])):
            if streak == 20:
                print("20 recorded in a row.  Assuming done...")
                return new_games
            game = game_history['matches'][i]
            if (game['queue'] != 420 or
               game['season'] != core.CURRENT_SEASON):
                continue
            else:
                '''print("Checking if game " +
                      str(game['gameId']) + " already recorded.")'''
                patch_major, patch_minor = conn.game_exists(
                    str(game['gameId']), region)
                if patch_major is not -1:
                    print("Data already recorded.")
                    if ((patch_major < core.PATCH_MAJOR) or
                       (patch_minor < core.PATCH_MINOR)):
                        print("No longer on current patch...")
                        return new_games
                    streak += 1
                else:
                    '''print("Adding game " + str(game['gameId']) +
                          " to list of new game.")'''
                    new_games.append(game['gameId'])
        conn.close()
        new_games = games_collect(player, region, new_games,
                                    time_begin - 604800000,
                                    time_begin, streak)
        return new_games
    except KeyError:  # Encountered if no games found (404)
        return new_games


def collect_region_worker(region, players, add_stats=True):
    shuffle = False
    while True:
        try:
            if shuffle:
                random.shuffle(players)
            for player in players:
                print("\nCollecting new matches for " + str(player['playerID']) + "...")
                new_games = games_collect(player, region, None)
                if add_stats:
                    print("\nAdding stats for new matches...\n")
                    stats.game_stats_add(new_games, region)
                sys.stdout.flush()
        except Exception as err:
            print(err)
            print("Error encountered. Starting again.")
        shuffle = True


# Start of data aggregation function.  Gets list of high-rank summoners, and
# feeds portions of the list to separatred processes
def collect_region(region):
    conn = db.Connection()
    players = conn.players_elite_get(region)
    conn.close()
    processes = []
    players_split = core.splitter(6, players)
    for player_group in players_split:
        process = multiprocessing.Process(target=collect_region_worker,
                                      args=(region, player_group,))
        processes.append(process)
        process.start()
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
