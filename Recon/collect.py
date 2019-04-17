"""
This module is responsible for the data aggregation
component of the application.
"""

from Recon import stats
from Recon import gametier
from Recon import core
from Recon import database as db

import random
import multiprocessing
import threading
import json
import datetime
import sys


# Retrieves stats for every player from given match, and returns stats
def game_data_get(gameID, region):
    conn = db.Connection()
    game_info = conn.game_info_get(gameID, region)
    conn.close()
    if len(game_info) == 0 or game_info[0]['gd.gameKey'] is None:
        print("Match data for " + str(gameID) + " does not exist.  "
              "Adding to database...")
        url = ("https://" + region.lower() +
               ".api.riotgames.com/lol/match/v4/matches/" + str(gameID))
        try:
            response = core.api_get(url).json()
            game_data = json.dumps(response)
            tier, players = gametier.gametier_calc(response, region)
            version = response['gameVersion'].split('.')
            patch_major = int(version[0])
            patch_minor = int(version[1])
            conn = db.Connection()
            if len(game_info) == 0:
                key = None
            else:
                key = game_info[0]['gameKey']
            key = conn.game_save(gameID, tier, patch_major, patch_minor, region, game_data, key)
            conn.close()
            if (patch_major < core.PATCH_MAJOR or
                    patch_minor < core.PATCH_MINOR):
                    print("Game is not on current patch...")
                    return -2, -2, -2, -2
            return response, tier, key, players
        except AttributeError as e:
            print("AttributeError")
            print(e)
            return -1, -1, -1, -1
    else:
        # TODO update this section to pull in playerKeys
        tier = game_info[0]['rank']
        key = game_info[0]['gameKey']
        print("Match data for " + str(key) + " already exists.  Loading...")
        conn = db.Connection()
        if not conn.champ_stats_full(key):
            game_data = conn.game_data_get(key)
            player_keys = {}
            for each in game_data['participantIdentities']:
                player_id = each['player']['summonerId']
                player = conn.player_get(player_id,region)[0]
                player_keys[player['summonerID']] = player['playerKey']
            conn.close()
            return game_data, tier, key, player_keys
        else:
            print("Fully added data, no need for pull matchData.")
            game_data = tier = key = players = -1
            conn.close()
            return game_data, tier, key, players


# Collects entire list of matches for given summoner,
# starting from time defined in Header.py
def games_collect(player, region, new_games=[],
                   time_begin=None, time_end=None, streak=0):
    if time_end is None:
        time_epoch = datetime.datetime.utcfromtimestamp(0)
        time_now = datetime.datetime.now()
        #time_now = time_now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_end = int((time_now - time_epoch).total_seconds() * 1000)
        time_begin = time_end - 604800000
    account_id = player['accountID']
    url = ("https://" + region.lower() +
           ".api.riotgames.com/lol/match/v4/matchlists/by-account/" +
           str(account_id) + "?queue=420&beginTime=" + str(time_begin) +
           "&endTime=" + str(time_end))
    try:
        game_history = core.api_get(url).json()
        total_games = game_history['totalGames']
        if total_games == 0:
            return new_games
        conn = db.Connection()
        for i in range(len(game_history['matches'])):
            if streak == 10:
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


def collect_region_worker(region, players, add_stats=True, shuffle=False):
    while True:
        try:
            if shuffle:
                random.shuffle(players)
            for player in players:
                print("\nCollecting new matches for " + str(player['playerID']) + "...")
                new_games = games_collect(player, region)
                if add_stats and len(new_games) > 0:
                    print("\nAdding stats for new matches...\n")
                    stats.game_stats_add(new_games, region)
                sys.stdout.flush()
        except Exception as err:
            print(err)
            print("Error encountered. Starting again.")
        shuffle = True


# Start of data aggregation function.  Gets list of high-rank summoners, and
# feeds portions of the list to separatred processes
def collect_region(region, is_multiprocessing = True):
    conn = db.Connection()
    players = conn.players_elite_get(region)
    conn.close()
    if is_multiprocessing:
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
    else:
        collect_region_worker(region, players)