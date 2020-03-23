import requests
import os
import shutil
import time
from bs4 import BeautifulSoup
import re
from modules.common import validatePageInput
from modules.common import printProgressBar
from modules.common import ordinal

log_file_name = "booru-downloader.log"
pid_step = 42
last_page_parent_tag = "a"
last_page_child_tag = "alt"
last_page_text = "last page"
preview_element_type = "div"
preview_element_subtype = "class"
preview_element_name = "thumbnail-preview"
api_posts_url = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1"
api_tags_url = "https://gelbooru.com/index.php?page=dapi&s=tag&q=index&json=1"
normal_posts_url = "https://gelbooru.com/index.php?page=post&s=list"
domain_name = ""
prefix = ""

extensions = (
    ('.webm', r"\.webm"),
    ('.mp4', r"\.mp4"),
    ('.gif', r"\.gif"),
    ('.png', r"\.png"),
    ('.jpeg', r"\.jpeg"),
    ('.jpg', r"\.jpg"),
)

def init(**data):
    global log_file_name, pid_step, last_page_parent_tag, last_page_child_tag, last_page_text, preview_element_type, preview_element_subtype, preview_element_name, api_posts_url, api_tags_url, normal_posts_url, domain_name, prefix
    log_file_name = data["log file name"]
    pid_step = data['pid step']
    last_page_parent_tag = data['last page parent tag']
    last_page_child_tag = data['last page child tag']
    last_page_text = data['last page text']
    preview_element_type = data['preview element type']
    preview_element_subtype = data['preview element subtype']
    preview_element_name = data['preview element name']
    api_posts_url = data['api posts url']
    api_tags_url = data['api tags url']
    normal_posts_url = data['normal posts url']
    domain_name = data['domain name']
    prefix = data['prefix']

def getPageFromPID(pid) -> int:
    page = 1
    if pid is None:
        return int(page)
    else:
        return int(pid/pid_step+1)

def getPidFromPage(page) -> int:
    return (int(page)-1)*pid_step

def getPID(url) -> int:
    pid = 0
    temp = re.search("pid=\d+$", url)
    if not temp:
        temp = re.search("pid=\d+(?=&)", url)
        if not temp:
            return pid
    return int(re.search("\d+", temp[0]).group(0))

def getTagsFromUrl(url) -> str:
    r = re.search("tags=.+(?=&)", url)
    return r[0]

def getLastPage(soup):
    a = soup.find(last_page_parent_tag, {last_page_child_tag: last_page_text})
    b = a.get('href')
    return getPID(b)

def changePage(url, page):
    expression = '&pid=\d+$'
    properPid = "&pid=" + str(getPidFromPage(page))
    searchObj = re.search(expression, url)
    if searchObj:
        address = re.sub(expression, properPid, str(url))
    else:
        address = url + properPid
    return address

def getNumberOfImages(soup):
    return len(soup.findAll(preview_element_type, {preview_element_subtype: preview_element_name}))

def convertTagsToUrl(tags):
    tag_string = "&tags="
    a = tags.split(',')
    for element in a:
        tag_string+=element.strip() + "+"
    return tag_string[:-1]

def getPageMetadata(url, tags, path, page, session):
    url = changePage(url, page)
    r = session.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    number_of_images = getNumberOfImages(soup)
    request_url = api_posts_url + '&limit=' + str(number_of_images) + convertTagsToUrl(tags) + '&pid=' + str(int(page)-1)
    print("request url for api:",request_url)
    r = session.get(request_url)
    return r.json()

def getImagesMetadata(json_elements):
    list_of_dictionaries = []
    print("Getting images metadata...")
    for element in json_elements:
        request_url = api_tags_url + '&names=' + element['tags']
        print("metadata request url:",request_url)
        r = requests.get(request_url)
        try:
            request_json = r.json()
        dictionary = {
            'artist': 'Unknown',
            'character': 'Unknown',
            'series': 'Unknown',
        }
        artist = ""
        character = ""
        series = ""
        for tag in request_json:
            if tag['type'] == 'artist':
                artist+=tag['tag'] + ','
            elif tag['type'] == 'character':
                character+=tag['tag'] + ','
                dictionary['character'] = tag['tag']
            elif tag['type'] == 'copyright':
                series+=tag['tag'] + ','
                dictionary['series'] = tag['tag']
        dictionary['artist'] = artist
        dictionary['character'] = character
        dictionary['series'] = series
        list_of_dictionaries.append(dictionary)
    print("Collected images metadata...")
    return list_of_dictionaries

def getImageUrls(json):
    list_of_urls = []
    print("Getting image URLs...")
    for element in json:
        url = "https://" + prefix + '.' + domain_name + "/" + "images" + "/" + element['directory'] + "/" + element['image']
        list_of_urls.append(url)
    print("Collected image URLs")
    return list_of_urls

def getImageExtensions(list_of_urls):
    list_of_extensions = []
    for url in list_of_urls:
        for extension in extensions:
            if re.search(extension[1], url):
                list_of_extensions.append(extension[0])
    return list_of_extensions
                

def downloadPage(image_urls, dictionary_metadata, image_extensions, path, session):
    printProgressBar(0, len(image_urls), 'Downloading...', 'Complete', length=50)
    for i in range(0, len(image_urls)):
        extension = image_extensions[i]
        filename = str("Artist: " + dictionary_metadata[i]['artist'] + " Character: " + dictionary_metadata[i]['character'] + " Series: " + dictionary_metadata[i]['series'] + ' ' + str(int(time.time())))
        filename = re.sub('/', '', filename)
        full_path = os.path.join(str(path), filename)
        try:
            r = session.get(image_urls[i], stream=True)
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
                full_path = full_path[0:245] + full_path[-10:0]
                with open(full_path, 'wb') as out_file:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, out_file)
        del r
        time.sleep(1)
        printProgressBar(i+1, len(image_urls), 'Downloading...', 'Complete', length=50)

def runBooru(url, tags, path, pages, session):
    if url == None:
        url = normal_posts_url + convertTagsToUrl(tags)
    page = pages[0]
    url = changePage(url, page)
    r = session.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    last_page = getLastPage(soup)
    pages = validatePageInput(last_page, pages)
    for page in pages:
        print("Downloading",ordinal(int(page)),"page.")
        url = changePage(url, page)
        print(url)
        json = getPageMetadata(url, tags, path, page, session)
        image_urls = getImageUrls(json)
        dictionary_metadata = getImagesMetadata(json)
        image_extensions = getImageExtensions(image_urls)
        downloadPage(image_urls, dictionary_metadata, image_extensions, path, session)
    
