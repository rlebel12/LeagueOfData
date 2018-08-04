"""
Basic interface for performing application functions
"""

#import updateDatabase as updb
from Recon.Aggregation import collect
from Recon.Analysis import cache
from Recon.Analysis.count import count
from Recon.Utility import champDict as cd
import sys
import os


if __name__ == '__main__':
    while(1):
        if len(sys.argv) == 1:
            numOptions = 8
            print("\nOptions: ")
            print("[1]: Add match data")
            print("[2]: Update Challenger and Master tiers")
            print("[3]: Update player information")
            print("[4]: Fill character tracker from matches")
            print("[5]: Count recorded matches and players")
            print("[6]: Fill character cache")
            print("[7]: Update champion hash table")
            print("[" + str(numOptions) + "]: Exit")

            choice = int(input("\nPlease enter a choice: "))
            while ((choice < 1 or choice > numOptions) and (choice != 100)):
                choice = int(input("Invalid choice.  Please try again: "))
        else:
            choice = int(sys.argv[1])
        if choice == 1:
            try:
                if len(sys.argv) == 3:
                    region = sys.argv[2]
                else:
                    region = input("[NA1, KR]: ").upper()
                while region not in ['NA1', 'KR']:
                    region = input("[NA1, KR]: ").upper()
                collect.collect_region('NA1')
            except KeyboardInterrupt:
                pass
        elif choice == 2:
            try:
                print()
                for region in ['NA', 'KR']:
                    updb.updateTopSumms(region)
            except:
                pass
        elif choice == 3:
            print()
            try:
                region = input("Select a region to",
                               "gather stats for [NA, KR]: ").upper()
                while region not in ['NA', 'KR']:
                    region = input("Invalid region.  Please",
                                   "try again [NA, KR]: ").upper()
                updb.updateSumms(region)
            except KeyboardInterrupt:
                pass
        elif choice == 4:
            try:
                region = input("Select a region to gather stats for [NA1, KR]: ")
                while region.upper() not in ['NA1', 'KR']:
                    region = input("Invalid region.  Please",
                                   "try again [NA1, KR]: ").upper()
                addWinStats.parse_stats(region.upper())
            except KeyboardInterrupt:
                pass
        elif choice == 5:
            count()
        elif choice == 6:
            charCache.main()
        elif choice == 7:
            cd.update()
        elif choice == numOptions:
            sys.exit()
        print()
    input("Press any key to exit...")
