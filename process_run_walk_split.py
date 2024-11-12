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
        self.runs = []
    
    def addRun(self, run):
        self.runs.append(run)
    
    def total(self):
        if len(self.runs) == 0:
            return RunInfo(0.0, 0.0)
        else:
            return sum(self.runs, RunInfo(0.0, 0.0))
        
class StatsManager:
    def __init__(self, dailyStats):
        self.weeklyStats = OrderedDict()

        sortedStats = OrderedDict(sorted(dailyStats.items(), key=lambda x: x[0]))

        for date in sortedStats:
            stat = sortedStats[date]
            yearAndWeek = self.__getYearAndWeek(date)
            if yearAndWeek in self.weeklyStats:
                self.weeklyStats[yearAndWeek].addRun(stat)
            else:
                newWeek = WeeklyStats(date)
                newWeek.addRun(stat)
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
activity_types = ["running", "trail_running"]
out_path = "run_walk.csv"

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
    if activity["hasSplits"] is False:
        raise Exception("Activity must have splits")
    
    splits = activity["splitSummaries"]
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
                runInfo = parse_run_walk(activity)

                doubleInfo = runInfo + runInfo

                if date in dailyStats:
                    dailyStats[date] = dailyStats[date] + runInfo
                else:
                    dailyStats[date] = runInfo

# Build the running stats manager
runningStats = StatsManager(dailyStats)

# Get list of stats for each week from start of stats
weeklyRunningStats = runningStats.toList()

for weeklyStats in weeklyRunningStats:
    runInfo = weeklyStats.total()
    print("%s: %.2fmi run, %.2fmi walk" % (write_date(weeklyStats.date), runInfo.distRun, runInfo.distWalk))

with open(out_path, 'w', newline='') as csvfile:
    fieldnames = ['Date', 'Run (mi)', 'Walk (mi)']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for weeklyStats in weeklyRunningStats:
        runInfo = weeklyStats.total()
        dateStr = write_date(weeklyStats.date)
        writer.writerow({fieldnames[0]: dateStr, fieldnames[1]: runInfo.distRun, fieldnames[2]: runInfo.distWalk})