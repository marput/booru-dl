import re
import requests
from bs4 import BeautifulSoup
import readline, glob
from lxml.html import fromstring
import os
import random
from random import choice
from decimal import Decimal, getcontext

tokens = (
  ('DIGIT', re.compile(r"(?<!\.)\b[0-9]+\b(?!\.)")),
  ('FLOAT', re.compile(r"[0-9]*\.?[0-9]+")),
  ('RANGE', re.compile('-')),
  ('TERMINATOR', re.compile(';')),
  ('STRING', re.compile('.')), 
)

def getRandomProxy():
    response = requests.get("https://sslproxies.org/")
    soup = BeautifulSoup(response.content, 'html.parser')
    proxy = {'https': 'https://' + choice(list(map(lambda x:x[0]+':'+x[1], list(zip(map(lambda x:x.text, 
	   soup.findAll('td')[::8]), map(lambda x:x.text, soup.findAll('td')[1::8]))))))}
    return proxy

def getProxy():
    unchecked_proxies = set()
    checked_proxies = set()
    url = 'https://free-proxy-list.net/' 
    page = requests.get(url) 
    soup = BeautifulSoup(page.text, 'html.parser')
    proxy_list_table = soup.find(id="proxylisttable")
    table_elements = soup.findAll(name="tr")
    print("Table elements:",len(table_elements))
    for i in range(1,min(len(table_elements), 200)):
        individual_elements = table_elements[i].findAll('td')
        print("Individual elements:",len(individual_elements))
        #[0] is ip address
        #[1] is port
        #[2] is country code
        #[3] is country
        #[4] is anonimity
        #[5] is google?
        #[6] supports https?
        #[7] last updated
        if individual_elements[6].text == 'yes':
            unchecked_proxies.add('https://' + individual_elements[0].text + ':' + individual_elements[1].text)
    proxy_count = 0
    for element in unchecked_proxies:
        url = "https://example.com"
        proxy_dict = {
            'http': element,
            'https': element
        }
        try:
           r = requests.get(url, proxies=proxy_dict, timeout=5) 
           print(r.ok)
           checked_proxies.add(element)
           print("Success! Good proxy")
           proxy_count+=1
        except ConnectionError as e:
            print("Bad proxy, removing...",e)
            continue
        except requests.exceptions.SSLError as ssl:
            print("Bad proxy, removing...",ssl)
            continue
        except requests.exceptions.ConnectTimeout as ct:
            print("Bad proxy, removing...",ct)
            continue
        except requests.exceptions.ProxyError as pe:
            print("Bad proxy, removing...",pe)
            continue
        if proxy_count >= 5:
            return checked_proxies
    return checked_proxies
            
list_of_urls = (
    'https://www.whatismybrowser.com/guides/the-latest-user-agent/opera',
    'https://www.whatismybrowser.com/guides/the-latest-user-agent/chrome',
    'https://www.whatismybrowser.com/guides/the-latest-user-agent/firefox',
)

def getUserAgents():
    user_agents = []
    for element in list_of_urls:
        url = element
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        user_agent_strings = soup.findAll(class_="code")
        for thing in user_agent_strings:
            text = str(thing.text)
            user_agents.append(text)
    return user_agents

def getRandomUserAgent(user_agents):
    return random.choice(user_agents)
        
def getUncleanTokens(userInput, tokens):
    tempArray = userInput.split(",")
    userInputArray = []
    for i in range(0, len(tempArray)):
        userInputArray.append(tempArray[i].strip())
        uncleanTokens = []
        for i in range(0, len(userInputArray)):
            text = userInputArray[i].strip()
            results = tokenizer(text, tokens)
            for j in range(0, len(results)):
                uncleanTokens.append((results[j][0], results[j][1]))
    return uncleanTokens

def cleanPageUserInput(uncleanTokens):
    cleanTokens = []
    value = ""
    for i in range(0, len(uncleanTokens)):
        if uncleanTokens[i][0] != 'STRING':
            value = uncleanTokens[i][1]
            if uncleanTokens[i][0] == 'DIGIT':
                value = int(value.lstrip('0'))
            cleanTokens.append((uncleanTokens[i][0], value))
    return cleanTokens

def checkRangeCondition(cleanTokens, i):
		if cleanTokens[i-1][0] == 'DIGIT' and cleanTokens[i+1][0] == 'DIGIT':
			return True
		else:
			return False


def parsePageUserInput(cleanTokens):
    listOfPages = []
    for i in range(0, len(cleanTokens)):
        if cleanTokens[i][0] == 'DIGIT':
            listOfPages.append(cleanTokens[i][1])
        elif cleanTokens[i][0] == 'RANGE':
            if checkRangeCondition(cleanTokens, i):
                listOfPages.pop()
                start = cleanTokens[i-1][1]
                end = cleanTokens[i+1][1]
                if start < end:
                    listOfPages.extend(range(start, end))
                    listOfPages.append(end)
                elif end < start:
                    listOfPages.extend(range(end, start))
                    listOfPages.append(start)
                elif start == end:
                    listOfPages.append(end)
        elif cleanTokens[i][0] == 'TERMINATOR':
            return listOfPages
    return listOfPages

def checkValidPages(listOfPages, lastPage):
    i = 0
    while 0 <= i < len(listOfPages):
        if not 1 <= int(listOfPages[i]) < lastPage+1:
            del listOfPages[i]
            i-=1
        i+=1
    return listOfPages

def checkIfPageRange(listOfPages):
    if len(listOfPages) > 0:
        return True
    else:
        return False
    
def getUserPages(lastPage, tokens):
    while(True):
        uncleanTokens = getUncleanTokens(input("Enter pages to scrap images from. Separate inputs by commas, terminate with semicolon. Indicate range with -. Eg. 1-18, 25, 30-35;. There are " + str(lastPage) + " pages in total.\n"), tokens)
        cleanTokens = cleanPageUserInput(uncleanTokens)
        listOfPages = parsePageUserInput(cleanTokens)
        listOfPages = list(set(listOfPages))
        listOfPages = checkValidPages(listOfPages, lastPage)
        if checkIfPageRange(listOfPages):
            return listOfPages

def validatePageInput(lastPage, pages):
    uncleanTokens = getUncleanTokens(pages, tokens)
    cleanTokens = cleanPageUserInput(uncleanTokens)
    listOfPages = parsePageUserInput(cleanTokens)
    listOfPages = list(set(listOfPages))
    listOfPages = checkValidPages(listOfPages, lastPage)
    if not checkIfPageRange(listOfPages):
        print("Invalid page range, terminating...")
        sys.exit(1)
    return listOfPages

def tokenizer(s, tokens):
    i = 0
    lexeme = []
    while i < len(s):
        match = False
        for token, regex in tokens:
            result = regex.match(s, i)
            if result:
                lexeme.append((token, result.group(0)))
                i = result.end()
                match = True
                break
        if not match:
            raise Exception('lexical error at {0}'.format(i))
    return lexeme

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '#', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

def getAddress(session):
    while True:
        address = input("Enter the URL address you want to scrape: ")
        try:
            r = session.get(address)
            r.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            print ("Http Error:",errh)
            continue
        except requests.exceptions.ConnectionError as errc:
            print ("Error Connecting:",errc)
            continue
        except requests.exceptions.Timeout as errt:
            print ("Timeout Error:",errt)
            continue
        except requests.exceptions.RequestException as err:
            print ("Request exception:",err)
            continue
        return address

def completePath(text, state):
    return (glob.glob(text+'*' + '/')+[None])[state]

def getPath():
    while True:
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(completePath)
        path = input("Enter the path to directory where images will get saved to: ")
        path = os.path.expanduser(path)
        if os.path.isdir(path): 
            return path
        print("Path doesn't exist, try again.")
def floatRange(start, end):
    """
    Get a range between two Decimal types, with decimal places depending on the max between start and end decimal places.
    @params:
        start  -  Required : starting index (Decimal)
        end    -  Required : ending index   (Decimal)
    """
    list_of_numbers = []
    start_decimal_places = start.to_eng_string()[::-1].find('.') 
    end_decimal_places = end.to_eng_string()[::-1].find('.')
    max_decimal_places = max(start_decimal_places, end_decimal_places)
    getcontext().prec = max_decimal_places + 1 #because its fucked
    step = '0.'
    for i in range(0, max_decimal_places-1):
        step+='0'
    step+='1'
    step = Decimal(step)
    number = start
    while number <= end:
        list_of_numbers.append(number.to_eng_string())
        number = number + step
    return list_of_numbers

def cleanRatioUserInput(uncleanTokens):
    cleanTokens = []
    value = ""
    for i in range(0, len(uncleanTokens)):
        if uncleanTokens[i][0] != 'STRING':
            value = uncleanTokens[i][1]
            if uncleanTokens[i][0] == 'FLOAT':
                if uncleanTokens[i][1] == '0':
                    global downloadAll
                    downloadAll = True
                    break
                else:
                    value = Decimal(value.lstrip('0'))
            cleanTokens.append((uncleanTokens[i][0], value))
    return cleanTokens

def parseRatioUserInput(cleanTokens):
    list_of_ratios = []
    for i in range(0, len(cleanTokens)):
        if cleanTokens[i][0] == 'FLOAT':
            list_of_ratios.append(cleanTokens[i][1])
        elif cleanTokens[i][0] == 'RANGE':
            if checkRatioRangeCondition(cleanTokens, i):
                list_of_ratios.pop()
                start = Decimal(cleanTokens[i-1][1])
                end = Decimal(cleanTokens[i+1][1])
                if start < end:
                    list_of_ratios.extend(floatRange(start, end))
                elif end < start:
                    list_of_ratios.extend(floatRange(end, start))
                elif start == end:
                    list_of_ratios.append(end.to_eng_string())
        elif cleanTokens[i][0] == 'TERMINATOR':
            return list_of_ratios
    return list_of_ratios

def checkRatioRangeCondition(cleanTokens, i):
    if cleanTokens[i-1][0] == 'FLOAT' and cleanTokens[i+1][0] == 'FLOAT':
        return True
    else:
        return False

def getUserRatio(ratios):
	if not __debug__:
		print("==========> getUserRatio() <==========")
		print("getUserRatio starting ratio:",ratios)
	uncleanTokens = getUncleanTokens(ratios, tokens)
	cleanTokens = cleanRatioUserInput(uncleanTokens)
	listOfRatios = parseRatioUserInput(cleanTokens)
	return listOfRatios

def checkResolution(list_of_ratios, resolution):
	if not __debug__:
		print("==========> checkResolution <==========")
		print("Length of list of ratios:",len(list_of_ratios))
	for ratio in list_of_ratios:
		if not __debug__:
			print("Compare status of:",Decimal(ratio),"and",Decimal(resolution),"is",Decimal.compare(Decimal(ratio), Decimal(resolution)))
		if Decimal.compare(Decimal(ratio), Decimal(resolution)) == Decimal('0'):
			return True
	if not __debug__:
		print("==========< checkResolution >==========")
	return False


