import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup as bs
from pathlib import Path
from collections import defaultdict
import json

import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
#unique_pages = set() #Initializes Set to store unique pages



# Takes a URL and a response object and returns a list of filtered links from the response object.
def scraper(url, resp, save_to_disk=False, save_to_folder='scraped_pages'):
    links = extract_next_links(url, resp)
    filtered_links = [link for link in links if is_valid(link)]

    unique_page_json(url)

    #url_without_fragment = url.partition("#")[0]  # Remove fragment from the URL
    #unique_pages.add(url_without_fragment) # Add the URL without fragment to the unique_pages set

    # create temporary file with link's data for tokenizing purposes
    # Save content of current page to local file if save_to_disk is True
    # if save_to_disk:
    #     save_web_page(url, resp, save_to_folder)
    # print(filtered_links)
    # print(str(len(filtered_links)))
    return filtered_links


def tokenize(path) -> set:
    tokens = set()
    try:
        with open(path, 'r', encoding="utf-8", errors="ignore") as f:
            for line in f:
                newtokens = re.findall(r'[a-zA-Z0-9]+', line)
                for newtoken in newtokens:
                    tokens.add(newtoken.lower())
    except:
        return tokens

    return tokens


def save_web_page(url, resp, save_to_folder):
    folder_path = Path(save_to_folder)
    folder_path.mkdir(parents=True, exist_ok=True) # Make folder if it doesn't exist
    
    # Replace all non-alphanumeric characters with underscore + add html extension to file name
    file_name = re.sub(r"[^\w\-_\. ]", '_', url) + '.html' 
    
    file_name = file_name[:255] # Truncate file name if it's too long

    # Create a new file in the folder and write the content of the page to it
    file_path = folder_path / file_name
    with file_path.open('w') as f:            
        f.write(resp.raw_response.content)


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

    soupified = bs(resp.raw_response.content)   # BeautifulSoup object
    aTags = soupified.select('a')               # list of all <a> tags

    # get all hyperlinks from webpage
    hyperlinks = set()
    for link in aTags:
        try:
            if link['href'] != url and link['href'] != resp.url:
                hyperlinks.add(link['href'].partition("#")[0])

        except KeyError:
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
            + r"|odc|ppsx"                                           # extensions added by us
            + r")$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
    except AttributeError:
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

#print("Number of unique pages:", len(unique_pages))

def unique_page_json(url: str):
    with open('urls.json', 'r') as file:
        data = json.load(file)
    if url not in data:
        with open('urls.json', 'w') as file:
            data.append(url)
            json.dump(data, file)

def num_unique_pages():
    with open("urls.json", "r+") as f:
        urls = json.load(f)
        return len(urls)

# # file for storing all unique websites without fragment
# uniqueFiles.json
# set((each website, number of words), etc)  # HTML markup doesn’t count as words

# # file for number of unique subdomains
# from collections import defaultdict
# subdomains = defaultdict(int)

# parsed = urlparse(resp.url)
# subdomain[parsed.hostname] += 1
# # Sort this alphabetically


# def somefunc (url):
#     open urls.json
#         if url is not in url.json's dict.keys
#             add url to json where key = url, value =  0
