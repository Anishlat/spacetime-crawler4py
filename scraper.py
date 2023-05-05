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


'''
Returns the tokens found in a piece of text.
    Params:
        text: A piece of text to go through
    Returns:
        (tokens: list[str], tokenCount: int): List of tokens and size of list
'''
def tokenize(text) -> tuple(list[str], int):
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
Get all subdomains and their counts from data/urls.json.
    Returns:
        subdomain_counts (dict[str]->int): dictionary of subdomains and their counts
'''
def count_subdomains():
    # load the URLs from the JSON file
    with open("/Users/jerrychen/Desktop/UCI/Spring23/INF141/subdom/urlsSorted.json", 'r') as f:
        urls = json.load(f)["urls"]

    # count the occurrences of each subdomain
    subdomain_counts = {}
    for url in urls:
        parsed_url = urlparse(url)
        if parsed_url.hostname.endswith('.ics.uci.edu'):
            subdomain = parsed_url.hostname.split('.')[0]  # get the first part of the hostname
            if subdomain not in subdomain_counts:
                subdomain_counts[subdomain] = 0
            subdomain_counts[subdomain] += 1

    # return the result as a dictionary
    return subdomain_counts


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


def top50commonwords() -> list(): # returns list of top 50 common words ordered by frequency.

    # stopwords is a set because a set is more efficient to access elements in terms of time complexity, compared to a list
    stopwords = {"able","about","above","abroad","according","accordingly","across","actually","adj","after","afterwards","again","against","ago","ahead","ain't","all","allow","allows","almost","alone","along","alongside","already","also","although","always","am","amid","amidst","among","amongst","an","and","another","any","anybody","anyhow","anyone","anything","anyway","anyways","anywhere","apart","appear","appreciate","appropriate","are","aren't","around","as","a's","aside","ask","asking","associated","at","available","away","awfully","back","backward","backwards","be","became","because","become","becomes","becoming","been","before","beforehand","begin","behind","being","believe","below","beside","besides","best","better","between","beyond","both","brief","but","by","came","can","cannot","cant","can't","caption","cause","causes","certain","certainly","changes","clearly","c'mon","co","co.","com","come","comes","concerning","consequently","consider","considering","contain","containing","contains","corresponding","could","couldn't","course","c's","currently","dare","daren't","definitely","described","despite","did","didn't","different","directly","do","does","doesn't","doing","done","don't","down","downwards","during","each","edu","eg","eight","eighty","either","else","elsewhere","end","ending","enough","entirely","especially","et","etc","even","ever","evermore","every","everybody","everyone","everything","everywhere","ex","exactly","example","except","fairly","far","farther","few","fewer","fifth","first","five","followed","following","follows","for","forever","former","formerly","forth","forward","found","four","from","further","furthermore","get","gets","getting","given","gives","go","goes","going","gone","got","gotten","greetings","had","hadn't","half","happens","hardly","has","hasn't","have","haven't","having","he","he'd","he'll","hello","help","hence","her","here","hereafter","hereby","herein","here's","hereupon","hers","herself","he's","hi","him","himself","his","hither","hopefully","how","howbeit","however","hundred","i'd","ie","if","ignored","i'll","i'm","immediate","in","inasmuch","inc","inc.","indeed","indicate","indicated","indicates","inner","inside","insofar","instead","into","inward","is","isn't","it","it'd","it'll","its","it's","itself","i've","just","k","keep","keeps","kept","know","known","knows","last","lately","later","latter","latterly","least","less","lest","let","let's","like","liked","likely","likewise","little","look","looking","looks","low","lower","ltd","made","mainly","make","makes","many","may","maybe","mayn't","me","mean","meantime","meanwhile","merely","might","mightn't","mine","minus","miss","more","moreover","most","mostly","mr","mrs","much","must","mustn't","my","myself","name","namely","nd","near","nearly","necessary","need","needn't","needs","neither","never","neverf","neverless","nevertheless","new","next","nine","ninety","no","nobody","non","none","nonetheless","noone","no-one","nor","normally","not","nothing","notwithstanding","novel","now","nowhere","obviously","of","off","often","oh","ok","okay","old","on","once","one","ones","one's","only","onto","opposite","or","other","others","otherwise","ought","oughtn't","our","ours","ourselves","out","outside","over","overall","own","particular","particularly","past","per","perhaps","placed","please","plus","possible","presumably","probably","provided","provides","que","quite","qv","rather","rd","re","really","reasonably","recent","recently","regarding","regardless","regards","relatively","respectively","right","round","said","same","saw","say","saying","says","second","secondly","see","seeing","seem","seemed","seeming","seems","seen","self","selves","sensible","sent","serious","seriously","seven","several","shall","shan't","she","she'd","she'll","she's","should","shouldn't","since","six","so","some","somebody","someday","somehow","someone","something","sometime","sometimes","somewhat","somewhere","soon","sorry","specified","specify","specifying","still","sub","such","sup","sure","take","taken","taking","tell","tends","th","than","thank","thanks","thanx","that","that'll","thats","that's","that've","the","their","theirs","them","themselves","then","thence","there","thereafter","thereby","there'd","therefore","therein","there'll","there're","theres","there's","thereupon","there've","these","they","they'd","they'll","they're","they've","thing","things","think","third","thirty","this","thorough","thoroughly","those","though","three","through","throughout","thru","thus","till","to","together","too","took","toward","towards","tried","tries","truly","try","trying","t's","twice","two","un","under","underneath","undoing","unfortunately","unless","unlike","unlikely","until","unto","up","upon","upwards","us","use","used","useful","uses","using","usually","v","value","various","versus","very","via","viz","vs","want","wants","was","wasn't","way","we","we'd","welcome","well","we'll","went","were","we're","weren't","we've","what","whatever","what'll","what's","what've","when","whence","whenever","where","whereafter","whereas","whereby","wherein","where's","whereupon","wherever","whether","which","whichever","while","whilst","whither","who","who'd","whoever","whole","who'll","whom","whomever","who's","whose","why","will","willing","wish","with","within","without","wonder","won't","would","wouldn't","yes","yet","you","you'd","you'll","your","you're","yours","yourself","yourselves","you've","zero","a","how's","i","when's","why's","b","c","d","e","f","g","h","j","l","m","n","o","p","q","r","s","t","u","uucp","w","x","y","z","I","www","amount","bill","bottom","call","computer","con","couldnt","cry","de","describe","detail","due","eleven","empty","fifteen","fifty","fill","find","fire","forty","front","full","give","hasnt","herse","himse","interest","itse”","mill","move","myse”","part","put","show","side","sincere","sixty","system","ten","thick","thin","top","twelve","twenty","abst","accordance","act","added","adopted","affected","affecting","affects","ah","announce","anymore","apparently","approximately","aren","arent","arise","auth","beginning","beginnings","begins","biol","briefly","ca","date","ed","effect","et-al","ff","fix","gave","giving","heres","hes","hid","home","id","im","immediately","importance","important","index","information","invention","itd","keys","kg","km","largely","lets","line","'ll","means","mg","million","ml","mug","na","nay","necessarily","nos","noted","obtain","obtained","omitted","ord","owing","page","pages","poorly","possibly","potentially","pp","predominantly","present","previously","primarily","promptly","proud","quickly","ran","readily","ref","refs","related","research","resulted","resulting","results","run","sec","section","shed","shes","showed","shown","showns","shows","significant","significantly","similar","similarly","slightly","somethan","specifically","state","states","stop","strongly","substantially","successfully","sufficiently","suggest","thered","thereof","therere","thereto","theyd","theyre","thou","thoughh","thousand","throug","til","tip","ts","ups","usefully","usefulness","'ve","vol","vols","wed","whats","wheres","whim","whod","whos","widely","words","world","youd","youre"}

    commons = {} # contains all words (ignoring stopwords) and its freq from tokenFrequency.json
    top50 = [] # list of the top 50 common words by freq

    with open('data/tokenFrequency.json', 'r') as file:
        data = json.load(file)

        for word in data:
            if word not in stopwords:
                frq = 0
                for val in data[word]:
                    frq += val[1]
                commons[word] = frq

    sorted_commons = dict(sorted(commons.items(), key = lambda x: x[1], reverse = True)) # sorting the dict by value in descending order

    for i in range(0, 50):
        top50.append(list(sorted_commons)[i])
    
    return top50