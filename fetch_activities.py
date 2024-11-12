#!/usr/bin/env python3

import json
import logging
import os
import datetime

from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

activity_path = "activities/"

# Load environment variables if defined
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:
        # Using Oauth1 and OAuth2 token files from directory
        print(
            f"Trying to login to Garmin Connect using token data from directory '{tokenstore}'...\n"
        )

        # Using Oauth1 and Oauth2 tokens from base64 encoded string
        # print(
        #     f"Trying to login to Garmin Connect using token data from file '{tokenstore_base64}'...\n"
        # )
        # dir_path = os.path.expanduser(tokenstore_base64)
        # with open(dir_path, "r") as token_file:
        #     tokenstore = token_file.read()

        garmin = Garmin()
        garmin.login(tokenstore)

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            # Ask for credentials if not set as environment variables
            if not email or not password:
                email, password = get_credentials()

            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(tokenstore)
            print(
                f"Oauth tokens stored in '{tokenstore}' directory for future use. (first method)\n"
            )
            # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(tokenstore_base64)
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
            )
        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError, requests.exceptions.HTTPError) as err:
            logger.error(err)
            return None

    return garmin

def write_activity(activity, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(activity, f, ensure_ascii=False, indent=4)

def parse_datetime(timeStr):
    return datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S")

api = init_api(email, password)

today = datetime.date.today()
startdate = datetime.datetime(2024, 1, 1)

print("Fetching activities...")
activities = api.get_activities_by_date(
    startdate.isoformat(), today.isoformat(), "")
numActivities = len(activities)
print("Saving %d activities to local storage" % (numActivities))

for i in range(0, numActivities):
    activity = activities[i]
    typeStr = activity["activityType"]["typeKey"]
    activityId = activity["activityId"]

    startTime = parse_datetime(activity["startTimeLocal"])
    fileName = startTime.strftime("%Y-%m-%d") + "_" + str(activityId) + ".json"

    filePath = activity_path + typeStr + "/" + fileName
    print("(%d of %d) Writing %s" % (i+1, numActivities, filePath))
    write_activity(activity, filePath)



"""last_activity = api.get_last_activity()"""
"""splitSummaries = last_activity["splitSummaries"]
numSplits = len(splitSummaries)
for i in range(0, numSplits):"""

