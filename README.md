# Mastodon Bot: Twitter Crawler

## Introduction

Mastodon Bot crawling tweets from Twitter accounts.

This was initially developed to collect official notices from an online game. Unfortunately, there were no other alternative channels to crawl info from..

## Disclaimer

**Please refrain from creating bots to track individuals.**

I don't hold any liability against any damages or losses from using my project.

It is highly recommended to set the toot's visibility to `private` to ensure that your bot isn't polluting the entire Federation.


##  Installation & Usage

The project is tested in Python 3.10, Debian 11

```bash
$ # Install dependencies
$ pip3 install -r requirements.txt
$ # Setup your environment file (Refer to .env.example)
$ cp .env.example .env
$ vi .env
$ # Run and see if everything works.
$ python3 main.py
```

You may also keep `systemd/mastodonbot.service` to run the bot running as daemon.

```bash
$ cp systemd/mastodonbot.service /etc/systemd/system/mastodonbot.service
$ systemctl daemon-reload
$ systemctl enable mastodonbot
$ systemctl start mastodonbot
```
