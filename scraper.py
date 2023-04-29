import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup as bs
from pathlib import Path
import json
import lxml.html
import lxml.etree
from difflib import SequenceMatcher
import bisect
from collections import defaultdict

# import nltk
# nltk.download('stopwords')
# from nltk.corpus import stopwords


# Takes a URL and a response object and returns a list of filtered links from the response object.
def scraper(url, resp, save_to_disk=False, save_to_folder='scraped_pages'):
    filtered_links = []
    try:
        if (is_valid(resp.url)):
            document = lxml.html.document_fromstring(resp.raw_response.content)         # html document
            if len(document.text_content()) < 50000:                                    # avg word size 4.7 chars * 10,000 words
                tokens, wordCount = tokenize(document.text_content())
                store_link(resp.url, wordCount)                                         # store {link : word count} into data/urls.json
                store_word_to_url_frequency(resp.url, tokens)

                links = extract_next_links(url, resp)                                   # links found from resp.url
                filtered_links = [link for link in links if is_valid(link)]             # only if links are valid

    except AttributeError:          # Nonetype
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
    # If status code != 200, error, return empty list
    if (resp.status != 200):
        return []

    soupified = bs(resp.raw_response.content, features='lxml')   # BeautifulSoup object
    aTags = soupified.select('a')                                # list of all <a> tags

    # get all hyperlinks from webpage
    hyperlinks = set()
    for link in aTags:
        try:
            if link['href'] != url and link['href'] != resp.url:    # ignore self-referential link
                hyperlinks.add(link['href'].partition("#")[0])

        except KeyError:    # no link given with 'href' tag
            pass

    return list(hyperlinks)


# Decide whether to crawl this url or not. 
# If you decide to crawl it, return True; otherwise return False.
# There are already some conditions that return False.
def is_valid(url):
    try:
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
            + r"|odc|ppsx|git|ps"                             # extensions added by us
            + r")$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
    except AttributeError:
        return False

    if is_link_similar(url):    # ignore links with high similarity >95%
        return False

    return True


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


# given a list of strings via bs4
# return: tuple of 3 items: set of tokens, # of tokens, # of total words (includes repititons)
def tokenize(text) -> (list[str], int, int):
    tokens = defaultdict(int)

    try:
        newtokens = re.findall(r'[a-zA-Z0-9]+', text)
        for newtoken in newtokens:
            tokens[newtoken.lower()] += 1
            # tokens.append(newtoken.lower())
    except:
        return (tokens, len(tokens))

    return (tokens, len(tokens))


def store_link(url : str, wordCount : int):
    with open('data/urls.json', 'r') as file:
        data = json.load(file)
    with open('data/urls.json', 'w') as file:
        data[url] = wordCount
        json.dump(data, file, indent=4)

    with open('data/urlsSorted.json', 'r') as file:
        data = json.load(file)
        loc = bisect.bisect(data["urls"], url)
        data["urls"].insert(loc, url)
    with open('data/urlsSorted.json', 'w') as file:
        # bisect.insort(data["urls"], url)       # added url into sorted list, O(log(N))
        json.dump(data, file, indent=4)


# Get number of unique webpages crawled
def num_unique_pages():
    data = None
    with open("data/urls.json", "r") as file:
        data = json.load(file)
    return len(data)


def is_link_similar(s : str) -> bool:
    tr = False
    with open('data/urls.json', 'r') as file:
        data =  json.load(file)
        idx = bisect.bisect(data["urls"], s)
        if len(data["urls"]) >= 3 and idx != 0 and idx != len(data["urls"]) - 1:
            diff1 = SequenceMatcher(None, s, data["urls"][idx - 1]).ratio()
            diff2 = SequenceMatcher(None, s, data["urls"][idx + 1]).ratio()
            if diff1 >= 0.95 or diff2 >= 0.95:
                tr = True
    return tr


def store_word_to_url_frequency(url, tokens): 
    with open('data/tokenFrequency.json', 'r') as file:
        data = json.load(file)
    with open('data/tokenFrequency.json', 'w') as file:
        for word in tokens:
            if word not in data:
                data[word] = [[url, tokens[word]]]
            else:
                data[word].append([url, tokens[word]])

        json.dump(data, file, indent=4)