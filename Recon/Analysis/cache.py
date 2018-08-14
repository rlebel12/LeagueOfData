"""
Fills out ChampCache table with data summaries for use when clients make requests for champion data
"""

from Recon.Utility import core
from Recon.Utility import database as db


# Continues buidling stat summary (existing dictionary of lists) with new stats (dictionary)
def createStatSummary(statSummary, newStats, keys):
    for key in keys:
        if key not in statSummary:
            statSummary[key] = [newStats[key]]
        else:
            statSummary[key].append(newStats[key])
    return statSummary


def createNewCharacterCharts(row, group, timeTotal, winTotal, winCount):
    champ = row['champ']
    dur = row['duration']
    result = row['result']
    if result == 1:
        winCount = winCount+1
    if champ not in timeTotal:
        time = [dur]
        win = [result]
        timeTotal[champ] = time
        winTotal[champ] = win
    elif champ in timeTotal:
        timeTotal[champ].append(dur)
        winTotal[champ].append(result)
    return winCount


def setupGraph(group, flag, timeTotal, winTotal):
    for key in timeTotal:
        time = []
        win = []
        for i in range(len(timeTotal[key])):
            time.append(timeTotal[key][i])
            win.append(winTotal[key][i])
        (allGames,allWins) = partitionDuration(time, win)
        ratio = []
        for i in range(len(allGames)):
            if allGames[i] == 0: ratio.append(0)
            else: ratio.append(allWins[i]/allGames[i])
        return ratio, len(timeTotal[key])


# Splits a list of match durations and a list of match outcomes into groups based on match duration
def partitionDuration(time, win): #a:0-25, b: 25-30, c: 35-40, d: 40-45, e: 45+
    a,b,c,d,e=0,0,0,0,0
    aw,bw,cw,dw,ew=0,0,0,0,0
    for each in time:
        i = time.index(each)
        if 0<=each<1500:
            a+=1
            aw = aw + win[i]
        elif 1500<=each<1800:
            b+=1
            bw = bw+win[i]
        elif 1800<=each<2100:
            c+=1
            cw += win[i]
        elif 2100<=each<2400:
            d+=1
            dw += win[i]
        elif 2400<=each:
            e+=1
            ew += win[i]
    allGames = [a,b,c,d,e]
    allWins = [aw,bw,cw,dw,ew]
    return (allGames,allWins)


# TODO
def createCharacterCharts(arr, group):
    #champDict = getIDChampDict()
    wantedStatKeys = ['kills','deaths','assists','totalDamageDealtToChampions','largestMultiKill','largestKillingSpree','turretKills','totalTimeCrowdControlDealt','goldEarned','totalMinionsKilled','neutralMinionsKilledTeamJungle','neutralMinionsKilledEnemyJungle','totalHeal','totalDamageTaken']
    for region in ['NA1', 'KR']:
        for entry in arr:
            conn = db.Connection()
            champID = entry['champID']
            matches = conn.champ_stats_get(core.PATCH_MAJOR, core.PATCH_MINOR, region, champID)
            timeTotal = {}
            winTotal = {}
            statSummary = {}
            winCount = 0.0
            print("Matches this patch for " + entry['champName'] + " in " + region + ": " + str(len(matches)))
            if(len(matches)) != 0:
                for match in matches:
                    matchKey = match['gameKey']
                    createStatSummary(statSummary, match, wantedStatKeys)
                    winCount = createNewCharacterCharts(match, group, timeTotal, winTotal, winCount)
                    #print(str(champID) + ": " + str(timeTotal) + ", " + str(winTotal))
                numMatches = len(statSummary['kills'])
                for key in statSummary.keys():
                    total = 0.0
                    for datum in statSummary[key]:
                        total += datum
                    statSummary[key] = total / numMatches
                    #print(key + ": " + str(statSummary[key]))
                totalRatio = winCount / len(winTotal[champID])
                #print(str(champID) + ": " + str(len(winTotal[champID])) + " matches, " + str(winCount) + " wins. Ratio: " + str(totalRatio))
                data, length = setupGraph(group, True, timeTotal, winTotal)
                query = '''SELECT * FROM ChampCache WHERE champ = %s AND patchMajor = %s AND patchMinor = %s AND region = %s'''
                conn = db.Connection()
                results = conn.execute(query, (champID, core.PATCH_MAJOR, core.PATCH_MINOR, region))
                statSummary = core.json.dumps(statSummary)
                if len(results) == 0:
                    query = '''INSERT INTO ChampCache (champ, patchMajor, patchMinor, durWRSize, durWRStats, totalWRStats, statSummary, region) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'''
                    conn.execute(query, (champID, core.PATCH_MAJOR, core.PATCH_MINOR, length, str(data), totalRatio, statSummary, region))
                else:
                    query = '''UPDATE ChampCache SET durWRSize=%s, durWRStats=%s, totalWRStats=%s, statSummary=%s, lastUpdated=CURRENT_TIMESTAMP WHERE champ=%s AND patchMajor = %s AND patchMinor = %s AND region = %s'''
                    conn.execute(query, (length, str(data), totalRatio, statSummary, champID, core.PATCH_MAJOR, core.PATCH_MINOR, region))

            else:
                query = '''SELECT COUNT(*) FROM ChampCache WHERE champ = %s AND patchMajor = %s AND patchMinor = %s AND region = %s'''
                results = conn.execute(query, (champID, core.PATCH_MAJOR, core.PATCH_MINOR, region))[0]
                if results == 0:
                    query = '''INSERT INTO ChampCache(champ, patchMajor, patchMinor, totalWRStats, region) VALUES (%s, %s, %s, %s, %s)'''
                    conn.execute(query, (champID, core.PATCH_MAJOR, core.PATCH_MINOR, 0, region))
            del conn


def main():
    started = core.time.time()
    conn = db.Connection()
    group = 'COMPETITIVE'
    arrs = conn.execute("SELECT * FROM ChampHash")
    arrs = core.splitter(10, arrs)
    threads = []
    for each in arrs:
        t = core.threading.Thread(target=createCharacterCharts, args=(each, group))
        t.daemon = True
        threads.append(t)
        t.start()
    for t in threads: t.join()
    print("Done.")
    print(core.time.time()-started)
