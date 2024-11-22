#!/usr/bin/env python3

import json
import logging
import os
import datetime
from collections import OrderedDict
import csv
from collections import namedtuple

class RunInfo:
    def __init__(self):
        self.distRun = 0.0
        self.distWalk = 0.0

    def __init__(self, distRun, distWalk):
        self.distRun = distRun
        self.distWalk = distWalk

    def __add__(self, other):
        return RunInfo(self.distRun + other.distRun, self.distWalk + other.distWalk)

class WeeklyStats:
    def __init__(self, date):
        (year, week, _) = date.isocalendar()
        self.date = date.fromisocalendar(year, week, 1)
        self.stats = dict()
    
    def add(self, name, stat):
        if name in self.stats:
            self.stats[name] = self.stats[name] + stat
        else:
            self.stats[name] = stat

    def getStatNames(self):
        return self.stats.keys()
    
    def hasStat(self, name):
        return name in self.stats

    def getStat(self, name):
        return self.stats[name]
        
class StatsManager:
    def __init__(self):
        self.weeklyStats = OrderedDict()

    def addDailyStats(self, name, dailyStats):
        sortedStats = OrderedDict(sorted(dailyStats.items(), key=lambda x: x[0]))

        for date in sortedStats:
            stat = sortedStats[date]
            self.addStat(date, name, stat)

    def addStat(self, date, name, stat):
        yearAndWeek = self.__getYearAndWeek(date)
        if yearAndWeek in self.weeklyStats:
                self.weeklyStats[yearAndWeek].add(name, stat)
        else:
            newWeek = WeeklyStats(date)
            newWeek.add(name, stat)
            self.weeklyStats[yearAndWeek] = newWeek
    
    def getWeeklyStats(self, date):
        (year, week, _) = date.isocalendar()
        key = (year, week)
        if key in self.weeklyStats:
            return self.weeklyStats[key]
        else:
            return WeeklyStats(date)
        
    def getStartDate(self):
        (year, week) = next(iter(self.weeklyStats))
        return date.fromisocalendar(year, week, 1)
    
    def getLastDate(self):
        (year, week) = next(reversed(self.weeklyStats))
        return date.fromisocalendar(year, week, 1)
    
    def toList(self):
        startDate = self.getStartDate()
        endDate = self.getLastDate()
        dateStride = datetime.timedelta(weeks=1)

        statsList = []
        while startDate <= endDate:
            statsList.append(self.getWeeklyStats(startDate))
            startDate = startDate + dateStride
        
        return statsList
    
    def __getYearAndWeek(self, date):
        iso = date.isocalendar()
        return (iso.year, iso.week)


activity_path = "activities/"
all_activity_types = subDirs = next(os.walk(activity_path))[1]
activity_types = all_activity_types
out_path = "weekly_stats.csv"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def meters_to_miles(meters):
    cm = 100.0 * meters
    inch = cm / 2.54
    miles = (inch / 12) / 5280

    return miles

def parse_date(timeStr):
    return datetime.datetime.strptime(timeStr.split(" ")[0], "%Y-%m-%d")

def write_date(date):
    return date.strftime("%Y-%m-%d")

def parse_run_walk(activity):    
    splits = activity["splitSummaries"]
    if len(splits) == 0:
        raise Exception("Activity must have splits")
    
    distRun = 0.0
    distWalk = 0.0

    for split in splits:
        splitType = split["splitType"]
        splitDist = split["distance"]

        if splitType == "RWD_RUN":
            distRun = splitDist
        elif splitType == "RWD_WALK":
            distWalk = splitDist
    
    return RunInfo(meters_to_miles(distRun), meters_to_miles(distWalk))

def parse_variable(activity, name):
    if not name in activity:
        raise Exception("\"%s\" not found in activity" % (name))
    return activity[name]

def parse_active_calories(activity):
    totalCalories = parse_variable(activity, "calories")
    restingCalories = parse_variable(activity, "bmrCalories")

    return totalCalories - restingCalories

stat_name = "Active Calories"

# Load all activity info from files
# Combine multiple activities from single day into single entry
dailyStats = dict()
for activity_type in activity_types:
    folder = activity_path + activity_type + "/"
    
    for filename in os.listdir(folder):
        f = os.path.join(folder, filename)
        if os.path.isfile(f):
            with open(f, 'r') as file:
                activity = json.load(file)
                date = parse_date(activity["startTimeLocal"])
                activeCalories = 0

                try:
                    activeCalories = parse_active_calories(activity)
                except Exception as e:
                    print("%s: Invalid activity (%s)" % (filename, e))

                if date in dailyStats:
                    dailyStats[date] = dailyStats[date] + activeCalories
                else:
                    dailyStats[date] = activeCalories

# Build the stats manager
stats = StatsManager()
stats.addDailyStats(stat_name, dailyStats)

# Get list of stats for each week from start of stats
weeklyStats = stats.toList()

for weeklyStat in weeklyStats:
    totalActiveCalories = 0
    if weeklyStat.hasStat(stat_name):
        totalActiveCalories = weeklyStat.getStat(stat_name)
    print("%s: %f Calories" % (write_date(weeklyStat.date), totalActiveCalories))

with open(out_path, 'w', newline='') as csvfile:
    fieldnames = ['Date', 'Active Calories']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for weeklyStat in weeklyStats:
        totalActiveCalories = 0
        if weeklyStat.hasStat(stat_name):
            totalActiveCalories = weeklyStat.getStat(stat_name)
        dateStr = write_date(weeklyStat.date)
        writer.writerow({fieldnames[0]: dateStr, fieldnames[1]: totalActiveCalories})