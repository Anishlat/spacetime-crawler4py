import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup as bs
import lxml.html
import lxml.etree
from collections import defaultdict
import json
from difflib import SequenceMatcher 
import bisect

# import nltk
# nltk.download('stopwords')
# from nltk.corpus import stopwords


# Takes a URL and a response object and returns a list of filtered links from the response object.
def scraper(url, resp, save_to_disk=False, save_to_folder='scraped_pages'):
    filtered_links = []
    try:
        if (is_valid(resp.url)):    # only proceed if the given link is valid, mainly to see if url is similar to processed urls

            links = extract_next_links(url, resp)   # links found from resp.url
            if links is None:   # no urls on webpage
                return []
            filtered_links = [link for link in links if is_valid(link)]                 # only if links are valid

            document = lxml.html.document_fromstring(resp.raw_response.content)         # html document
            if len(document.text_content()) < 50000:                                    # avg word size 4.7 chars * 10,000 words, rounded up
                tokens, wordCount = tokenize(document.text_content())                   # list of tokens, # of tokens
                store_link(resp.url, wordCount)                                         # store {link : word count} into data/urls.json
                store_word_to_url_frequency(resp.url, tokens)                           # store {tokens : [url, # of times token seen]} into data/tokensFrequency.json

    except AttributeError:          # None-type url
        return filtered_links
    except lxml.etree.ParserError:  # empty HTML document
        return []

    return filtered_links


# Implementation required.
# url: the URL that was used to get the page
# resp.url: the actual url of the page
# resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
# resp.error: when status is not 200, you can check the error here, if needed.
# resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
#         resp.raw_response.url: the url, again
#         resp.raw_response.content: the content of the page!
# Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
def extract_next_links(url, resp):
    if (resp.status != 200): # if status != 200 OK, ignore
        return None

    soupified = bs(resp.raw_response.content, features='lxml')   # BeautifulSoup object
    aTags = soupified.select('a')                                # list of all <a> tags

    # get all hyperlinks from webpage
    hyperlinks = set()
    for link in aTags:
        try:
            if link['href'] != url and link['href'] != resp.url:    # ignore self-referential link
                hyperlinks.add(link['href'].partition("#")[0])      # ignore fragment

        except KeyError:    # no link given with 'href' tag
            pass

    return list(hyperlinks)


# Decide whether to crawl this url or not. 
# If you decide to crawl it, return True; otherwise return False.
# There are already some conditions that return False.
def is_valid(url):
    try:
        if is_link_similar(url):    # ignore links with high similarity >95%
            return False

        parsed = urlparse(url)

        #invalid scheme
        if parsed.scheme not in set(["http", "https"]):
            return False

        #invalid hostname
        accepted_hostnames = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}   
        if not any([parsed.hostname.endswith(hostname) for hostname in accepted_hostnames]):
            return False

        # invalid file extension
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz"
            + r"|odc|ppsx|git|ps|bib"                             # extensions added by us
            + r")$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
    except AttributeError:  # url parsed incorrectly or is NoneType, does not have scheme attribute
        return False


# # file for storing tokens : website
# # tokensToLink.json
# dict()
# key = token
# values = [(website link, number of times token was found on said website), etc... for all websites with that token]
# # sort this list descending to get top 50 words, make sure to ignore stop words ^^
# sum([count for link, count in values]) # to get sum of times token was found
# set = stop words
# set(sum).difference(stop words) # might need to resort, should solve number 3

# IDEAS:
# Maybe initialize the dict outside of the function, then pass it in as a parameter? Since we are 
# processing files one by one, we can just add to the dict as we go along. Or maybe call this function
# recursively, and pass in the dict as a parameter, and then return the dict at the end?
'''
def commonWords(file_path):
    # Initialize an empty dictionary to store the word counts
    word_counts = {}

    # Read the contents of the file
    with open(file_path, 'r') as file:
        text = file.read()
        
        # Find all the words in the text, USE TOKENIZER INSTEAD
        words = pattern.findall(text)
        
        # Remove the English stop words from the words list
        words = [word.lower() for word in words if word.lower() not in stopwords.words('english')]
        
        # Count the frequency of each remaining word and add it to the word_counts dictionary
        for word in words:
            if word in word_counts:
                word_counts[word] += 1
            else:
                word_counts[word] = 1

    # Get the 50 most common words and write them to a new file
    with open('word_counts.txt', 'w') as file:
        for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:50]:
            file.write(f'{word} {count}\n')
'''


'''
Returns the tokens found in a piece of text.
    Params:
        text: A piece of text to go through
    Returns:
        (tokens: list[str], tokenCount: int): List of tokens and size of list
'''
def tokenize(text) -> (list[str], int):
    tokens = defaultdict(int)

    try:
        newtokens = re.findall(r'[a-zA-Z0-9]+', text)   # get all tokens
        for newtoken in newtokens:
            tokens[newtoken.lower()] += 1               # treat token as lowercase, increment its count
    except:
        return (tokens, len(tokens))

    return (tokens, len(tokens))


'''
Stores the url and associated word count into data/urls.json, alphabetical order version into data/urlsSorted.json
    Params:
        url (str): url to store
        wordCount (int): number of tokens or words in url
'''
def store_link(url : str, wordCount : int) -> None:
    # add url to urls mapped to total word count
    with open('data/urls.json', 'r') as file:
        data = json.load(file)
    with open('data/urls.json', 'w') as file:
        data[url] = wordCount
        json.dump(data, file, indent=4)     # pretty dumb (indentation)

    # add url into sorted list, for checking similarity between nearby links
    with open('data/urlsSorted.json', 'r') as file:
        data = json.load(file)
        loc = bisect.bisect(data["urls"], url)      # location for url to be added, O(log(N))
        data["urls"].insert(loc, url)               # add url at loc
    with open('data/urlsSorted.json', 'w') as file:
        json.dump(data, file, indent=4)     # pretty dumb (indentation)


'''
Get the number of unique urls from data/urls.json.
    Returns:
        count (int): number of urls
'''
def num_pages() -> int:
    data = 0
    with open("data/urls.json", "r") as file:
        data = json.load(file)
    return len(data)    # size of dictionary containing links


'''
Returns the tokens found in a piece of text.
    Params:
        s (str): url
    Returns:
        similar (bool): whether the url is too similar or not
'''
def is_link_similar(s : str) -> bool:
    tr = False
    with open('data/urlsSorted.json', 'r') as file:
        data =  json.load(file)
        idx = bisect.bisect(data["urls"], s)    # get supposed new index of url in sorted list
        try:
            if len(data["urls"]) >= 3:
                # similarity ratios, scaled 0-1
                diff0 = SequenceMatcher(None, s, data["urls"][idx - 2]).ratio()
                diff1 = SequenceMatcher(None, s, data["urls"][idx - 1]).ratio()
                diff2 = SequenceMatcher(None, s, data["urls"][idx]).ratio()
                diff3 = SequenceMatcher(None, s, data["urls"][idx + 1]).ratio()
                if diff0 >= 0.95 and diff1 >= 0.95:     # previous 2 are too similar
                    tr = True
                if diff2 >= 0.95 and diff3 >= 0.95:     # following 2 are too similar
                    tr = True
                if diff1 >= 0.95 and diff2 >= 0.95:     # surrounding 2 are too similar
                    tr = True
        except IndexError:      # indexOutOfBounds, ignore and move on to next
            pass
    return tr


'''
Returns the tokens found in a piece of text.
    Params:
        url (str): url
        tokens (dict[str]->count): 
'''
def store_word_to_url_frequency(url, tokens) -> None: 
    with open('data/tokenFrequency.json', 'r') as file:
        data = json.load(file)
    with open('data/tokenFrequency.json', 'w') as file:
        for word in tokens:
            if word not in data:
                data[word] = [[url, tokens[word]]]      # create the outer list if word has not been seen
            else:
                data[word].append([url, tokens[word]])  # else just append the current url and # of times the token was seen 

        json.dump(data, file, indent=2)
