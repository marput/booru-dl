import re
import subprocess
import requests
import os
import shutil
import time
import uuid
from bs4 import BeautifulSoup
from modules import exiftool
from modules.common import validatePageInput
from modules.common import printProgressBar
from modules.common import ordinal

_to_esc = re.compile(r'\s|,|:')
def _esc_char(match):
    return '\\' + match.group(0)
def escape(name):
    return _to_esc.sub(_esc_char, name)

log_file_name = "booru-dl.log"
normal_posts_url = "https://danbooru.donmai.us/posts?"
login_element_id = "session_name"
login_element_name = "session[name]"
password_element_name = "session[password]"
pagination_info = ("div", "class", "paginator")
base_url = "https://danbooru.donmai.us"
preview_info = ("article", "class", "post-preview")
artist_tag = ("li", "class", "tag-type-1")
character_tag = ("li", "class", "tag-type-4")
series_tag = ("li", "class", "tag-type-3")
tag_element = ("li", "class", "tag-type-0")
source_id = "post-information"
source_index = 3
tag_element_name = "data-tag-name"
full_image_id = "post-option-download"
post_url = "https://danbooru.donmai.us/session"
login_page = 'https://danbooru.donmai.us/login'

extensions = (
    ('.webm', r"\.webm"),
    ('.mp4', r"\.mp4"),
    ('.gif', r"\.gif"),
    ('.png', r"\.png"),
    ('.jpeg', r"\.jpeg"),
    ('.jpg', r"\.jpg"),
)

def init(**data):
    global log_file_name, normal_posts_url
    normal_posts_url = data['normal_posts_url']
    global login_element_id, login_element_name, password_element_name
    login_element_id = data['login_element_id']
    login_element_name = data['login_element_name']
    password_element_name = data['password_element_name']
    global pagination_info
    pagination_info = data['pagination_info']
    global base_url, preview_info
    base_url = data['base_url']
    preview_info = data['preview_info']
    global artist_tag, character_tag, series_tag, tag_element_name, full_image_id, tag_element, source_id, source_index
    artist_tag = data['artist_tag']
    character_tag = data['character_tag']
    series_tag = data['series_tag']
    tag_element = data['tag_element']
    source_id = data['source_id']
    source_index = data['source_index']
    tag_element_name = data['tag_element_name']
    full_image_id = data['full_image_id']
    global login_page, post_url
    login_page = data['login_page']
    post_url = data['post_url']
    
def logIn(login: str, password: str, s: requests.session) -> requests.session:
    if not __debug__:
        print("==========> logIn <==========")
    r = s.get(login_page)
    soup = BeautifulSoup(r.text, 'html.parser')
    form = soup.find(id=login_element_id).parent
    while form.find("form") is None:
        form = form.parent
    inputs = form.findAll("input")
    payload = {}
    for input in inputs:
        name = input.get('name')
        value = input.get('value')
        if not value:
            value = ""
        if name == login_element_name:
            if not __debug__:
                print("Found login input")
            value = login
        if name == password_element_name:
            if not __debug__:
                print("Found password input")
            value = password
        payload[name] = value
    print("Logging in...")
    s.post(post_url, data=payload)
    print("Logged in.")
    if not __debug__:
        print("Login url:")
        print("Post_Url:")
        print("Form:",form)
        print("Payload:",payload)
        print("Login:",login)
        print("Password:",password)
        print("Cookies:",s.cookies)
        print("==========< logIn >==========")
    return s

def changePage(url: str, page: int) -> str:
    if not __debug__:
        print("==========> changePage <==========")
        print("url",url)
    search = re.search(r'page=\d+', url)
    if not search:
        url = url + "&" + "page=" + str(page)
        if not __debug__:
            print("If not search url:",url)
    else:
        if not __debug__:
            print("Search:",search[0])
            print("Page",str(page))
        search = re.sub(r'\d+$', str(page), search[0])
        if not __debug__:
            print("Search[0]:",search[0])
            print("Search:",search)
        url = re.sub(r'page=\d+', search, url)
        if not __debug__:
            print("Final url:",url)
            print("==========< changePage >==========")
    return url

def getLastPage(soup: BeautifulSoup, s: requests.session, url: str) -> int:
    if not __debug__:
        print("==========> getLastPage <==========")
    paginator = soup.find(pagination_info[0], {pagination_info[1]: pagination_info[2]})
    if not __debug__:
        print("Pagination info 0:",pagination_info[0])
        print("Pagination info 1:",pagination_info[1])
        print("Pagination info 2:",pagination_info[2])
    elements = paginator.findAll('a')
    last_page = 0
    if not __debug__:
        print("Elements:",elements)
    #elements[-2] is the last numeric page
    if elements[-2].string == None:
        if not __debug__:
            print("No elements[-2] found")
        url = changePage(url, 1001)
        r = s.get(url)
        page = BeautifulSoup(r.text, 'html.parser')
        if re.search(r"page limit exceeded", soup.text, re.IGNORECASE):
            if not __debug__:
                print("Last page = 1000")
            last_page = 1000
        else:
            url = changePage(url, 2001)
            r = s.get(url)
            page = BeautifulSoup(r.text, 'html.parser')
            if re.search(r"page limit exceeded", soup.text, re.IGNORECASE):
                if not __debug__:
                    print("Last page = 2000")
                last_page = 2000
            else:
                if not __debug__:
                    print("Last page = 5000")
                last_page = 5000
    else:
        if not __debug__:
            print("Found elements[-2]")
        last_page = int(elements[-2].string)
    if not __debug__:
        print("Last page:",last_page)
        print("==========< getLastPage >==========")
    return last_page
            
def getImagePages(soup: BeautifulSoup) -> list:
    if not __debug__:
        print("==========> getImagePages() <==========")
    image_pages = []
    previews = soup.findAll(preview_info[0], {preview_info[1]: preview_info[2]})
    if not __debug__:
        print("Previews:",previews)
    for preview in previews:
        image_pages.append(str(base_url + preview.find('a').get('href')))
    if not __debug__:
        print("image_pages:",image_pages)
        print("==========< getImagePages() >==========")
    return image_pages

def getImageMetadata(image_pages: list, s: requests.session) -> list:
    print("Getting image metadata...")
    if not __debug__:
        print("==========> getImageMetadata() <==========")
    list_of_dictionaries = []
    for link in image_pages:
        character = ""
        artist = ""
        series = ""
        image = ""
        extension = ""
        tags = ""
        r = s.get(link)
        soup = BeautifulSoup(r.text, 'html.parser')
        artist_elements = soup.findAll(artist_tag[0], {artist_tag[1]: artist_tag[2]})
        if not __debug__:
            print("Artist elements:",artist_elements)
        for element in artist_elements:
            string = element.get(tag_element_name)
            if not __debug__:
                print("artist:",string)
            artist+=string + ","
        artist = artist[:-1]
        character_elements = soup.findAll(character_tag[0], {character_tag[1]: character_tag[2]})
        if not __debug__:
            print("Character elements:",character_elements)
        for element in character_elements:
            string = element.get(tag_element_name)
            if not __debug__:
                print("character:",string)
            character+=string + ","
        character = character[:-1]
        series_elements = soup.findAll(series_tag[0], {series_tag[1]: series_tag[2]})
        if not __debug__:
            print("Series elements:",series_elements)
        for element in series_elements:
            string = element.get(tag_element_name)
            if not __debug__:
                print("series:",series)
            series+=string + ","
        series = series[:-1]
        tag_elements = soup.findAll(tag_element[0], {tag_element[1]: tag_element[2]})
        if not __debug__:
            print("Tag elements:",tag_elements)
        for element in tag_elements:
            string = element.get(tag_element_name)
            tags+=string+","
        tags = tags[:-1]
        image = soup.find(id=full_image_id).get('href')
        if not __debug__:
            print("Get href...")
        if image == None:
            image = soup.find(id=full_image_id).get('src')
            if not __debug__:
                print("Get src...")
        if image == None:
            image = soup.find(id=full_image_id).find('a').get('href')
            if not __debug__:
                print("Get 'a', 'href'...")
        if not __debug__:
            print("Image:",image)
        for extension in extensions:
            if re.search(extension[1], image):
                extension = extension[0]
                break
        source = soup.find(id=source_id).findAll('li')[source_index].find('a')
        if source == None:
            source = "Unknown"
        else:
            source = source.get('href')
        dictionary = {
            'artist': artist,
            'series': series,
            'character': character,
            'image': image,
            'extension': extension,
            'tags': tags,
            'source': source,
        }
        list_of_dictionaries.append(dictionary)
    if not __debug__:
        print("==========< getImageMetadata() >==========")
    return list_of_dictionaries

def insertImageMetadata(image: str, dictionary_of_info: dict) -> None:
    command = "exiftool"
    flag = b"-overwrite_original"
    artist = ("-xmp:artist=" + dictionary_of_info['artist']).encode('utf-8')
    series = ("-xmp:copyright=" + dictionary_of_info['series']).encode('utf-8')
    character = ("-xmp:person=" + dictionary_of_info['character']).encode('utf-8')
    source = ("-xmp:source=" + dictionary_of_info['source']).encode('utf-8')
    tags = ("-xmp:description=" + dictionary_of_info['tags']).encode('utf-8')
    image = image.encode('utf-8')
    with exiftool.ExifTool() as et:
        et.execute(flag, artist, series, character, source, tags, image)

def insertVideoMetadata(video: str, extensionless_path: str, dictionary_of_info: dict) -> None:
    artist = "artist=" + dictionary_of_info['artist']
    series = "copyright=" + dictionary_of_info['series']
    character = "person=" + dictionary_of_info['character']
    source = "source=" + dictionary_of_info['source']
    tags = "description=" + dictionary_of_info['tags']
    subprocess.call(["ffmpeg",
                     "-i", video,
                     "-vcodec", "copy",
                     "-acodec", "copy",
                     "-metadata", artist,
                     "-metadata", series,
                     "-metadata", character,
                     "-metadata", source,
                     "-metadata", tags,
                     extensionless_path + "_tagged" + dictionary_of_info['extension']])
    subprocess.call(["rm", "-f", video])

def convertTagsToUrl(tags: str) -> str:
    if not __debug__:
        print("==========> convertTagsToUrl() <==========")
    tag_string = "tags="
    a = tags.split(',')
    for element in a:
        tag_string+=element.strip() + "++"
    if not __debug__:
        print("Tag string:",tag_string[:-1])
        print("==========< convertTagsToUrl() >==========")
    return tag_string[:-1]

def downloadImages(session: requests.session, path: str , list_of_dictionaries: list, m: bool) -> None:
    if not __debug__:
        print("==========> downloadImages() <==========")
        print("len of list of dic:",len(list_of_dictionaries))
    printProgressBar(0, len(list_of_dictionaries), 'Downloading...', 'Complete', length=50)
    for i in range(0, len(list_of_dictionaries)):
        ext = list_of_dictionaries[i]['extension']
        if isinstance(ext, tuple):
            ext = ext[0]
        #without_extension = str("Artist: " + list_of_dictionaries[i]['artist'] + " Character: " + list_of_dictionaries[i]['character'] + " Series: " + list_of_dictionaries[i]['series'] + ' ' + str(int(time.time())))
        without_extension = str(uuid.uuid4().hex)
        filename = without_extension + ext
        #filename = re.sub('/', '', filename)
        full_path = os.path.join(str(path), filename)
        full_path_extensionless = os.path.join(str(path), without_extension)
        try:
            r = session.get(list_of_dictionaries[i]['image'], stream=True)
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
        if (ext != '.webm' and ext != '.mp4') and m == True:
            if not __debug__:
                print("Not a webm and m flag is turned on")
            insertImageMetadata(full_path, list_of_dictionaries[i])
        elif (ext == '.webm' or ext == '.mp4') and m == True:
            if not __debug__:
                print("A webm and m flag is turned on")
            insertVideoMetadata(full_path, full_path_extensionless, list_of_dictionaries[i])
        else:
            print("Unknown file format. Skipping...")
            continue
        printProgressBar(i+1, len(list_of_dictionaries), 'Downloading...', 'Complete', length=50)
    if not __debug__:
        print("==========< downloadImages() >==========")

def runBooru(url: str, tags: str, path: str, pages: str, session: requests.session, login:str, password: str, m: bool):
    if not __debug__:
        print("==========> runBooru() <==========")
    if url == None:
        url = normal_posts_url + convertTagsToUrl(tags)
    if login != None:
        session = logIn(login, password, session)
    page = pages[0]
    if not __debug__:
        print("url:",url)
    url = changePage(url, page)
    r = session.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    last_page = getLastPage(soup, session, url)
    pages = validatePageInput(last_page, pages)
    for page in pages:
        print("Downloading",ordinal(int(page)),"page.")
        url = changePage(url, page)
        if not __debug__:
            print(url)
        r = session.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        image_pages = getImagePages(soup)
        list_of_dictionaries = getImageMetadata(image_pages, session)
        downloadImages(session, path, list_of_dictionaries, m)
    if not __debug__:
        print("==========< runBooru() >==========")
    
    
            
    


    
    
