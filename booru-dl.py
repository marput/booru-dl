import argparse
import os
import re
import requests
import sys
import importlib
from modules.common import getUserAgents
from modules.common import getRandomUserAgent

set_of_url_boorus = {
    ("gelboorubasedbooru", r"^http.*gelbooru\.com.+"),
    ("rule34xxx", r"^http.*rule34\.xxx.+"),
    ("danbooru_with_tags", r"^http.*danbooru\.donmai\.us.+"),
    ("lolibooru", r"^http.*lolibooru\.moe.+"),
    ("sakugabooru", r"^http.*sakugabooru\.com.+"),
    ("danbooru_with_tags", r"^http.*safebooru\.donmai\.us.+"),
    ("konachan", r"^http.*konachan\.net.+"),
    ("exhentai", r"^http.*e.hentai\.org.+"),
}
set_of_entered_boorus = {
    ("gelboorubasedbooru", r"gelbooru"),
    ("rule34xxx", r"rule34xxx|rule34.xxx"),
    ("danbooru_with_tags", r"danbooru|danbooru\.donmai|danbooru.donmai\.us"),
    ("lolibooru", r"lolibooru|lolibooru\.moe"),
    ("sakugabooru", r"sakugabooru|sakugabooru\.com"),
    ("danbooru_with_tags", r"safeboorud|safebooru\.donmai|safebooru\.donmai\.us"),
    ("konachan", r"konachan|konachan\.net"),
    ("exhentai", r"exhentai|e\-hentai|exhentai\.org|e\-hentai\.org"),
}

def determineBooru(url, booru):
    if url is None:
        for element in set_of_entered_boorus:
            if re.search(element[1], booru, re.IGNORECASE):
                return element[0]
    else:
        for element in set_of_url_boorus:
            if re.search(element[1], url):
                return element[0]
    print("Booru not supported, terminating...")
    sys.exit(1)

parser = argparse.ArgumentParser(description = "Command-line tool for downloading images from image boorus.")

#-url URL, -path PATH, -pages PAGES, -login LOGIN, -password PASSWORD
target = parser.add_mutually_exclusive_group(required=True)
panda = parser.add_mutually_exclusive_group(required=False)
target.add_argument("--url", metavar = "URL", type=str, help = "URL address to scrape from")
target.add_argument("--tags", metavar = "TAGS", type=str, help = "Tags to search images with")
panda.add_argument("--prioritize-torrent", dest = "prioritize_torrent", action="store_true", help = "Prioritize torrents when downloading from exhentai")
panda.add_argument("--torrent-only", dest="torrent_only", action="store_true", help = "Download torrent only")
parser.add_argument("--booru", metavar = "BOORU", type=str, required = "--tags" in sys.argv and not "--url" in sys.argv, help = "Booru to search tags on")
parser.add_argument("--ratios", metavar = "RATIOS", type=str, help = "Ratios of images on konachan")
parser.add_argument("--path", metavar = "PATH", required=False, type=str, default=os.path.abspath(os.path.curdir), help = "Path where images will get saved to")
parser.add_argument("--pages", metavar = "PAGES", required=False, type=str, default="1-999", help = "Pages you want to download images from")
parser.add_argument("--login", dest = "login", required = "--password" in sys.argv, type=str, help = "Login for the site you want to scrape from")
parser.add_argument("--password", dest = "password", type=str, required = "--login" in sys.argv, help = "Password for the site you want to scrape from")
parser.add_argument("-m", dest = "m", action="store_true", help = "Switch metadata write on. Requires exiftool for jpeg/png/gif and ffmpeg for webms")

args = parser.parse_args()
if not __debug__:
    print("URL {} tags {} path {} pages {} login {} password {} ratios {} m {}, prioritize_torrent {}, torrent_only {}".format(
    args.url,
    args.tags,
    args.path,
    args.pages,
    args.login,
    args.password,
    args.ratios,    
    args.m,
    args.prioritize_torrent,
    args.torrent_only,
))
booru = determineBooru(args.url, args.booru)
if booru == "konachan" and args.ratios == None: 
    print("Ratio required for konachan.")
    sys.exit(1)
elif booru != "konachan" and args.ratios != None:
    print("Ratios are only supported for konachan.")
    sys.exit(1)
if booru == "exhentai":
    if (re.search(r"exhentai", args.url) or re.search(r"exhentai|exhentai\.org", args.booru)) and args.login == None:
        print("You need to login to access exhentai.")
        sys.exit(1)
    elif (args.login == None or args.password == None) and args.torrent_only == False:
        print("You need to login to download original images on e-hentai/exhentai. If you don't want to log in, please inlcude the --torrent-only flag in the arguments.")
        sys.exit(1)
if not __debug__:
    print("Booru:",booru)
booru_lib = importlib.import_module("modules." + booru, package=None)
session = requests.session()
session.headers.update({"User-Agent": getRandomUserAgent(getUserAgents())})

if booru == "konachan":
    booru_lib.runBooru(args.url, args.tags, args.path, args.pages, args.ratios, session, args.login, args.password, args.m)
elif booru == "exhentai":
    booru_lib.runBooru(args.url, args.tags, args.path, args.pages, session, args.login, args.password, args.m, args.prioritize_torrent, args.torrent_only)
else:
    booru_lib.runBooru(args.url, args.tags, args.path, args.pages, session, args.login, args.password, args.m)

