import requests
import re
import time
import shutil
import sys
import os
import subprocess
import uuid
from bs4 import BeautifulSoup
from modules.common import validatePageInput
from modules.common import printProgressBar

log_file_name = "booru-dl.log"

def logIn(login: str, password: str, s: requests.session) -> requests.session:
    r = s.get("https://e-hentai.org/bounce_login.php?b=d&bt=1-1")
    post_url = "https://forums.e-hentai.org/index.php?act=Login&CODE=01"
    soup = BeautifulSoup(r.text, 'html.parser')
    form = soup.find('form')
    inputs = form.findAll("input")
    payload = {}
    for input in inputs:
        name = input.get('name')
        value = input.get('value')
        if not value:
            value = ""
        if name == "UserName":
            value = login
        elif name == "PassWord":
            value = password
        payload[name] = value
    print("Logging in...")
    s.post(post_url, data=payload)
    time.sleep(1)
    s.get("https://e-hentai.org")
    time.sleep(1)
    s.get("https://forums.e-hentai.org")
    time.sleep(1)
    s.get("https://exhentai.org")
    print("Logged in")
    return s

def getImageLimits(s: requests.session) -> tuple:
    r = s.get("https://e-hentai.org/home.php")
    soup = BeautifulSoup(r.text, 'html.parser')
    limit_text = soup.find(class_="homebox").find("p").findAll("strong")
    limit = (int(limit_text[0].string), int(limit_text[1].string))
    return limit

def getTagsFromGallery(soup: BeautifulSoup, path: str, gallery_name: str) -> None:
    taglist = soup.find(id="taglist")
    namespaces = taglist.findAll("td", {"class": "tc"})
    tds = taglist.findAll("td", attrs={"class": None})
    with open(str(os.path.join(path, gallery_name + ".txt")), "w") as file:
        for i in range(0, len(namespaces)):
            file.write(str(namespaces[i].string + " "))
            tags = tds[i].findAll("a")
            for tag in tags:
                file.write(str(tag.string + ", "))
            file.write("\n")

def getGalleryName(soup: BeautifulSoup) -> str:
    return soup.find(id="gn").string

def getListOfThumbnails(soup: BeautifulSoup) -> list:
    list_of_thumbnails = []
    gdt = soup.find(id="gdt")
    gallery_elements = gdt.findAll(class_="gdtm")
    if gallery_elements == None:
        gallery_elements = gdt.findAll(class_="gdtl")
    for element in gallery_elements:
        list_of_thumbnails.append(element.find("a").get("href"))
    return list_of_thumbnails

def getListOfImages(s: requests.session, list_of_thumbnails: list) -> list:
    list_of_images = []
    for thumbnail in list_of_thumbnails:
        if not __debug__:
            print("thumbnail:",thumbnail)
        r = s.get(thumbnail)
        soup = BeautifulSoup(r.text, 'html.parser')
        full_image = soup.find("div", id="i7").find("a")
        if full_image == None:
            full_image = soup.find(id="img").get("src")
        else:
            full_image = full_image.get("href")
        list_of_images.append(full_image)
    return list_of_images

def getGallerySize(soup: BeautifulSoup) -> str:
    size = soup.find("td", string=re.compile("[-+]?[0-9]*\.?[0-9]+ GB|[-+]?[0-9]*\.?[0-9]+ MB")).string
    return size

def getLastGalleryPage(soup: BeautifulSoup) -> int:
    ptt = soup.find(class_="ptt")
    last_page = int(ptt.findAll("td")[-2].string)
    return last_page

def getLastSitePage(soup: BeautifulSoup) -> int:
    ptb = soup.find(class_="ptb")
    if ptb == None:
        return 1
    last_page = int(ptb.findAll("td")[-2].string)
    return last_page

def changeGalleryPage(url: str, page: int) -> str:
    search = re.search(r"\?p=\d+", url)
    if not search:
        url = url + "?p=" + str(page-1) #because gallery pages are sorted from 0 to n-1
        return url
    url = re.sub(r"\?p=d+", str("?p=" + str(page-1)), url)
    return url

def downloadImages(s: requests.session, path: str, list_of_images: list) -> None:
    printProgressBar(0, len(list_of_images), "Downloading...", "Complete", length=50)
    for i in range(0, len(list_of_images)):
        r = s.head(list_of_images[i])
        if not __debug__:
            print("headers:",r.headers)
        try:
            temp = r.headers['content-disposition']
            filename = re.findall("filename=(.+)", temp)[0]
        except KeyError:
            try:
                temp = r.headers['location']
                temp = temp.rsplit('/', 1)[1].rsplit("?", 1)[0]
                filename = temp
            except KeyError:
                filename = str(i+1) + ".png"
        if not __debug__:
            print("filename:",filename)
            print("path",path)
        full_path = os.path.join(path, filename)
        if not __debug__:
            print("full_path:",full_path)
        try:
            r = s.get(list_of_images[i], stream=True)
            r.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            with open(log_file_name, 'a') as log_file:
                log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Http error:" + str(errh) + '\n')
            continue
        except requests.exceptions.ConnectionError as errc:
            with open(log_file_name, 'a') as log_file:
                log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Connection error:" + str(errc) + '\n')
            continue
        except requests.exceptions.Timeout as errt:
            with open(log_file_name, 'a') as log_file:
                log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Timeout error:" + str(errt) + '\n')
            continue
        except requests.exceptions.TooManyRedirects as errr:
            with open(log_file_name, 'a') as log_file:
                log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Redirects error:" + str(errr) + '\n')
            continue
        except requests.exceptions.RequestException as erre:
            with open(log_file_name, 'a') as log_file:
                log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Request error:" + str(erre) + '\n')
            continue
        try:
            with open(full_path, 'wb') as out_file:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, out_file)
        except OSError as exc:
            if exc.errno == 36:
                full_path = full_path[0:245] #+ full_path[-10:0]
                with open(full_path, 'wb') as out_file:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, out_file)
        del r
        time.sleep(1)
        printProgressBar(i+1, len(list_of_images), "Downloading...", "Complete", length=50)

def isThereTorrent(soup: BeautifulSoup):
    table = soup.find(id="gd5")
    paragraphs = soup.findAll("p", class_="g2")
    number = paragraphs[1].find("a").string
    number = re.search(r"\d+", number)[0]
    if int(number) > 0:
        return True
    return False

def getTorrents(soup: BeautifulSoup, s: requests.session):
    torrents = []
    table = soup.find(id="gd5")
    paragraphs = soup.findAll("p", class_="g2")
    paragraph = paragraphs[1]
    a = paragraph.find("a")
    link = re.search(r"(?<=return popUp\(').*(?=')", a.get("onclick"))
    print("link 0:",link[0])
    page = s.get(link[0])
    soup = BeautifulSoup(page.text, 'html.parser')
    torrentinfo = soup.find(id="torrentinfo")
    torrentboxes = torrentinfo.findAll("table", {"style": "width:99%"})
    for torrentbox in torrentboxes:
        size = torrentbox.find("td", {"style": "width:150px"}).text
        number = re.search(r"\d+", size)[0]
        multiplier = re.search(r"MB|GB", size)[0]
        size = (number, multiplier)
        try:
            link = torrentbox.find("a").get("href")
        except AttributeError:
            print("Torrent expunged, skipping...")
            continue
        dictionary = {
            "size": size,
            "link": link,
        }
        torrents.append(dictionary)
    return torrents

def compareTorrents(list_of_torrents: list) -> str:
    maximum = (-9999, "MB")
    for torrent in list_of_torrents:
        if torrent['size'][1] == "GB" and maximum[1] == "MB":
            maximum = (torrent['size'][0], torrent['size'][1])
            link = torrent['link']
        elif (torrent['size'][1] == "GB" and maximum[1] == "GB") or (torrent['size'][1] == "MB" and maximum[1] == "MB"):
            maximum = (max(int(torrent['size'][0]), int(maximum[0])), maximum[1])
            link = torrent['link']
    return link

def downloadTorrentFile(link: str, s: requests.session, path: str) -> None:
    r = s.head(link)
    if not __debug__:
        print("headers:",r.headers)
    try:
        temp = r.headers['content-disposition']
        filename = re.findall("filename=(.+)", temp)[0]
    except KeyError:
        try:
            temp = r.headers['location']
            temp = temp.rsplit('/', 1)[1].rsplit("?", 1)[0]
            filename = temp
        except KeyError:
            filename = str(uuid.uuid4().hex) + ".torrent"
    full_path = os.path.join(path, filename)
    try:
        r = s.get(link, stream=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        with open(log_file_name, 'a') as log_file:
            log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Http error:" + str(errh) + '\n')
    except requests.exceptions.ConnectionError as errc:
        with open(log_file_name, 'a') as log_file:
            log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Connection error:" + str(errc) + '\n')
    except requests.exceptions.Timeout as errt:
        with open(log_file_name, 'a') as log_file:
            log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Timeout error:" + str(errt) + '\n')
    except requests.exceptions.TooManyRedirects as errr:
        with open(log_file_name, 'a') as log_file:
            log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Redirects error:" + str(errr) + '\n')
    except requests.exceptions.RequestException as erre:
        with open(log_file_name, 'a') as log_file:
            log_file.write(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()) + " Request error:" + str(erre) + '\n')
    try:
        with open(full_path, 'wb') as out_file:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, out_file)
    except OSError as exc:
        if exc.errno == 36:
            full_path = full_path[0:245] + full_path[-10:0]
            with open(full_path, 'wb') as out_file:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, out_file)
    del r
    return ((full_path, path), filename)

def downloadTorrent(torrent: tuple) -> None:
    print("Opening",torrent[1])
    subprocess.Popen(["transmission-remote", "-a", torrent[0][0], "-w", torrent[0][1]])
    print("Opened",torrent[1])

def torrentOnly(s: requests.session, url: str, path: str, m: bool):
    r = s.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    gallery_name = getGalleryName(soup)
    if isThereTorrent(soup):
        gallery_size = getGallerySize(soup)
        full_path = os.path.join(os.path.expanduser(path), gallery_name)
        if not os.path.isdir(full_path):
            os.makedirs(full_path)
        if m:
            getTagsFromGallery(soup, full_path, gallery_name)
        print("Getting torrent links...")
        torrents = getTorrents(soup, s)
        print("Comparing torrents...")
        torrent = compareTorrents(torrents)
        print("Downloading torrent file...")
        torrent_file = downloadTorrentFile(torrent, s, full_path)
        downloadTorrent(torrent_file)
    else:
        print("No torrent found for the gallery",gallery_name,"and torrent_only flag is set, skipping...")

def prioritizeTorrent(s: requests.session, url: str, path: str, m: bool):
    r = s.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    gallery_name = getGalleryName(soup)
    if isThereTorrent(soup):
        gallery_size = getGallerySize(soup)
        full_path = os.path.join(os.path.expanduser(path), gallery_name)
        if not os.path.isdir(full_path):
            os.mkdir(full_path)
        if m != None:
            getTagsFromGallery(soup, full_path, gallery_name)
        print("Getting torrent links...")
        torrents = getTorrents(soup, requests.session)
        print("Comparing torrents...")
        torrent = compareTorrents(torrents)
        print("Downloading torrent file...")
        torrent_file = downloadTorrentFile(torrent, s, full_path)
        downloadTorrent(torrent_file)
    else:
        print("No torrent found for the gallery",gallery_name,"and prioritize_torrent flag is set, falling back to downloading original images...")
        limit = getImageLimits(s)
        print("Your current image limit is",limit[0],"out of",limit[1])
        if not __debug__:
            print("url before change",url)
        url = changeGalleryPage(url, 1)
        if not __debug__:
            print("url after change:",url)
        r = s.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        gallery_size = getGallerySize(soup)
        print("The gallery size is",gallery_size)
        gallery_name = getGalleryName(soup)
        full_path = os.path.join(os.path.expanduser(path), gallery_name)
        if not os.path.isdir(full_path):
            os.mkdir(full_path)
        if m != None:
            getTagsFromGallery(soup, full_path, gallery_name)
        last_page = getLastGalleryPage(soup)
        pages = list(range(1, last_page if last_page > 1 else 2))
        for page in pages:
            url = changeGalleryPage(url, page)
            print("Downloading",gallery_name,"currently on page",str(page),"out of",str(last_page))
            r = s.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            thumbnails = getListOfThumbnails(soup)
            images = getListOfImages(s, thumbnails)
            downloadImages(s, full_path, images)

def downloadOriginals(s: requests.session, url: str, path: str, m: bool):
    limit = getImageLimits(s)
    print("Your current image limit is",limit[0],"out of",limit[1])
    if not __debug__:
        print("url before change",url)
    url = changeGalleryPage(url, 1)
    if not __debug__:
        print("url after change:",url)
    r = s.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    gallery_size = getGallerySize(soup)
    print("The gallery size is",gallery_size)
    gallery_name = getGalleryName(soup)
    full_path = os.path.join(os.path.expanduser(path), gallery_name)
    if not os.path.isdir(full_path):
        os.mkdir(full_path)
    if m != None:
        getTagsFromGallery(soup, full_path, gallery_name)
    last_page = getLastGalleryPage(soup)
    pages = list(range(1, last_page if last_page > 1 else 2))
    for page in pages:
        url = changeGalleryPage(url, page)
        print("Downloading",gallery_name,"currently on page",str(page),"out of",str(last_page))
        r = s.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        thumbnails = getListOfThumbnails(soup)
        images = getListOfImages(s, thumbnails)
        downloadImages(s, full_path, images)

def downloadGallery(s: requests.session, url: str, path: str, m: bool, prioritize_torrent: bool, torrent_only: bool) -> None:
    if torrent_only: 
        torrentOnly(s, url, path, m)
    elif prioritize_torrent:
        prioritizeTorrent(s, url, path, m)
    else:
        downloadOriginals(s, url, path, m)

def determineUrlType(url):
    if url == None:
        return "tag"
    elif re.search(r"^http.*e.hentai.org/g/\d+/[a-zA-Z0-9]*/", url):
        return "gallery"
    elif re.search(r"^http.*e.hentai.org/\?.+", url) or re.search(r"/tag/", url):
        return "galleries"
    elif re.search(r"^http.*e.hentai.org/s/.*"):
        return "invalid"

def getMinimalGalleries(soup: BeautifulSoup) -> list:
    list_of_galleries = []
    print(soup.prettify())
    tds = soup.findAll("td", {"class": "gl3m glname"})
    for td in tds:
        list_of_galleries.append(td.find("a").get("href"))
    return list_of_galleries

def getCompactGalleries(soup: BeautifulSoup) -> list:
    list_of_galleries = []
    tds = soup.findAll("td", {"class": "gl3c glname"})
    for td in tds:
        list_of_galleries.append(td.find("a").get("href"))
    return list_of_galleries

def getExtendedGalleries(soup: BeautifulSoup) -> list:
    list_of_galleries = []
    tds = soup.findAll("td", {"class": "gl2e"})
    for td in tds:
        list_of_galleries.append(td.find("a").get("href"))
    return list_of_galleries

def getThumbnailGalleries(soup: BeautifulSoup) -> list:
    list_of_galleries = []
    divs = soup.findAll("div", {"class": "gl3t"})
    for div in divs:
        list_of_galleries.append(div.find("a").get("href"))
    return list_of_galleries

def getGalleryLinks(soup: BeautifulSoup) -> list:
    mode = soup.find("option", {"selected": "selected"}).string
    if mode == "Minimal" or mode == "Minimal+": 
        print("Minimal")
        list_of_galleries = getMinimalGalleries(soup)
    elif mode == "Compact":
        list_of_galleries = getCompactGalleries(soup)
    elif mode == "Extended":
        print("Extended")
        list_of_galleries = getExtendedGalleries(soup)
    elif mode == "Thumbnail":
        print("Thumbnail")
        list_of_galleries = getThumbnailGalleries(soup)
    return list_of_galleries

def changeSitePage(url: str, page: int) -> str:
    if re.search(r"/tag/", url):
        url = re.subn(r"\d+$", str(page-1), url)
        if url[1] == 0:
            url = url + str(page-1)
    else:
        url = re.subn(r"page=\d+", "page=" + str(page-1), url)
        if url[1] == 0:
            before = re.search(r".*(\?)", url)[0]
            after = re.search(r"\&(.*)", url)[0]
            url = before + "page=" + str(page-1) + after
            return url
    return url[0]

def downloadGalleries(session, url, path, tags, pages, m: bool, prioritize_torrent: bool, torrent_only: bool):
    if url != None:
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        last_page = getLastSitePage(soup)
        pages = validatePageInput(last_page, pages)
        for page in pages:
            url = changeSitePage(url, page)
            print(url)
            r = session.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            list_of_galleries = getGalleryLinks(soup)
            print(list_of_galleries)
            for gallery in list_of_galleries:
                downloadGallery(session, gallery, path, m, prioritize_torrent, torrent_only)
    else:
        print(url)
        print("Tags are not implemented yet")
        pass

def runBooru(url: str, tags: str, path: str, pages: list, session: requests.session, login: str, password: str, m: bool, prioritize_torrent: bool, torrent_only: bool):
    if not __debug__:
        print("run booru url:",url)
    if login != None:
        session = logIn(login, password, session)
    type = determineUrlType(url)
    if not __debug__:
        print(type)
    if type == "gallery":
        downloadGallery(session, url, path, m, prioritize_torrent, torrent_only)
    elif type == "galleries":
        downloadGalleries(session, url, path, tags, pages, m, prioritize_torrent, torrent_only)
    elif type == "tag":
        print("Downloading galleries based on tags not implemented (yet)")
        sys.exit(1)
    elif type == "invalid":
        print("Invalid URL")
        sys.exit(1)
    else:
        print("Unrecognized URL, terminating")
        sys.exit(1)
    
