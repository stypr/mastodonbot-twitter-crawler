#!/usr/bin/python -u
# -*- coding: utf-8 -*-

"""
main.py

Twitter crawler for Mastodon
"""

import os
import os.path
import time
import pickle
import logging
import requests
import tweepy
from dotenv import load_dotenv
from mastodon import Mastodon


### Init & Import Environment Variables


BOT = None
logging.basicConfig(level=logging.INFO)

load_dotenv()
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
INSTANCE_DOMAIN = os.getenv("INSTANCE_DOMAIN")
APP_NAME = os.getenv("APP_NAME")
BOT_USERNAME = os.getenv("BOT_USERNAME")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")


### Import & Parse Twitter Account List


TWITTER_ACCOUNT_ENV = os.getenv("TWITTER_ACCOUNT_LIST")
TWITTER_ACCOUNT_LIST = {}
for ACCOUNT in TWITTER_ACCOUNT_ENV.split("\n"):
    _account = ACCOUNT.strip()
    if not _account:
        continue
    _temp = _account.split(":")
    if len(_temp) == 1:
        _temp.append("en")
    TWITTER_ACCOUNT_LIST[_temp[0]] = _temp[1]

del TWITTER_ACCOUNT_ENV


### Storing last_tweet_id


def save_dict(value, filename="local.secret"):
    """
    Save dictionary to filename
    """
    with open(filename, "wb") as fhandle:
        pickle.dump(value, fhandle)


def load_dict(filename="local.secret"):
    """
    Load dictionary from filename
    """
    if not os.path.exists(filename):
        return {}

    with open(filename, "rb") as fhandle:
        return pickle.load(fhandle)


### Mastodon Authentication


def login():
    """
    Login to Mastodon. Returns the Mastodon object
    Register the app if the app never existed before
    """
    # Register app
    if not os.path.exists("client.secret"):
        Mastodon.create_app(
            APP_NAME,
            api_base_url=f"https://{INSTANCE_DOMAIN}",
            to_file="client.secret"
        )

    # Login
    mastodon = Mastodon(client_id="client.secret")
    mastodon.log_in(
        BOT_USERNAME,
        BOT_PASSWORD,
        to_file="user.secret"
    )

    # Use token for the instance
    mastodon = Mastodon(access_token="user.secret")
    return mastodon


### Mastodon Upload and Toot


def upload(media_file):
    """
    Upload file.
    `media_file` can be passed as a path or URL.
    When URL is passed, it also needs to retrieve the mime_type, as per per documentation.
    """
    mime_type = None
    if media_file.lower().startswith(("http://", "https://")):
        req = requests.get(
            media_file,
            headers={"User-Agent": "Mozilla/5.0 (X11)"},
            timeout=3
        )
        mime_type = req.headers["Content-Type"]
        media_file = req.content

    return BOT.media_post(
        media_file=media_file,
        mime_type=mime_type
    )


def toot(status, media_ids=None, visibility="private", language="ja"):
    """
    Write status
    Private visiblity with Japanese by default.
    """
    return BOT.status_post(
        status=status,
        media_ids=media_ids,
        visibility=visibility,
        language=language
    )


### Twitter Crawling


def crawl(screen_name, since_id=None):
    """
    Crawl tweets, parse images
    """
    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

    # Get user ID from screen name
    try:
        screen_id = client.get_user(username=screen_name).data.id
    except:
        return None

    # Tweets
    tweets = client.get_users_tweets(
        screen_id,
        max_results=5,
        since_id=since_id,
        tweet_fields=(
            "id,created_at,text,author_id,referenced_tweets,attachments,"
            + "entities,context_annotations,conversation_id"
        ),
        media_fields="media_key,duration_ms,height,preview_image_url,type,url,width,alt_text",
        expansions="attachments.media_keys",
        exclude="replies,retweets",
    )

    image_list = {}
    result = []

    if not tweets.data:
        return {"data": {}, "new_since_id": since_id}

    if tweets.includes:
        for image in tweets.includes.get("media", []):
            image_list[image["media_key"]] = {
                "url": image["url"]
                if image["type"] != "video"
                else image["preview_image_url"],
                "type": image["type"],
            }

    for tweet in tweets.data:
        _id = tweet.id
        _text = tweet.text
        _image = []

        try:
            for url in tweet.entities.get("urls", []):
                # Check if the URL is an image, if so, append to the image_list
                if url.get("media_key"):
                    if image_list.get(url["media_key"]):
                        _image.append(image_list[url["media_key"]])
                    _text = _text.replace(url["url"], "")
                else:
                    _text = _text.replace(url["url"], url["expanded_url"])
        except:
            pass

        result.append({"id": _id, "text": _text, "image": _image})

    return {
        "data": result,
        "new_since_id": tweets.meta["newest_id"]
    }


def post_tweets():
    """
    Main runner
    """
    last_id = load_dict()

    while True:
        for username, language in TWITTER_ACCOUNT_LIST.items():
            logging.info("Started crawling %s.", username)
            try:
                if last_id.get(username):
                    _crawl = crawl(username, last_id[username])
                else:
                    _crawl = crawl(username)

                for tweet in _crawl.get("data", {}):
                    image_list = []
                    for image in tweet.get("image", []):
                        image_list.append(upload(image["url"])["id"])

                    res = toot(
                        status=f"From @{username}\n\n{tweet['text']}",
                        media_ids=image_list,
                        visibility="private",  # visibility
                        language=language,
                    )
                    logging.debug(res)

                last_id[username] = _crawl["new_since_id"]
                save_dict(last_id)
                logging.info("Done crawling %s.", username)
                time.sleep(5)

            except Exception as exc:
                logging.exception(
                    "Error occured while checking %s: %s", username, str(exc)
                )

        logging.info("Wait for 5 minutes...")
        time.sleep(5 * 60)


### Main


if __name__ == "__main__":
    BOT = login()
    post_tweets()
