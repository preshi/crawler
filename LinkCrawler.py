import urllib.request as urlcon
from urllib.parse import urlparse
from urllib.parse import urlunparse
from bs4 import BeautifulSoup
import sys
import time
import threading
import traceback
from collections import deque

VISITED_URLS = {}
CRAWLED_URLS = {}
CRAWL_BUFFER = deque([])
CRAWLER_DEFAULT_WORKERS = 10
WORKER_WAIT_INTERVAL = 1 #seconds
MAX_COUNT_LIMIT = None

class WorkerThread(threading.Thread):
    def __init__(self, crawler, name):
        threading.Thread.__init__(self)
        self.__crawler = crawler
        self.name = name
        
    def run(self):
        '''Start function for each thread'''
        
        while not self.__crawler.kill and self.is_alive():
            try:
                if len(CRAWL_BUFFER) > 0:
                    strURL = CRAWL_BUFFER.popleft()
                    urlObj = URL(strURL)
                    print("URL " + str(urlObj.url) + " about to be crawled by Worker : " + str(self.name))
                    self.__crawler.crawl(urlObj)
                else:
                    print("No work for worker :" + str(self.name))
                time.sleep(WORKER_WAIT_INTERVAL)
            except Exception as e:
                print("Unknown exception occured while doing worker task" + str(e))
                traceback.print_exc()
        print("Stopping Worker : " + str(self.name))

class URL():
    def __init__(self,strURL):
        self.url = strURL
        self.netloc = None
        self.scheme = None
        self.valid = True
        self.validateURL()
    
    def validateURL(self):
        '''Validate the URL's scheme and netloc'''
        
        pURL = urlparse(self.url)
        if pURL.netloc:
            self.netloc = pURL.netloc
        else:
            self.valid = False
        if pURL.scheme:
            self.scheme = pURL.scheme
        else:
            self.valid = False

class WebCrawler():
    _lock = threading.Lock()
    kill = False
    count = 0
    listworkers = []
    def __init__(self):
        self.activeWorkers = []
        self.__startWorkers()

    def __startWorkers(self):
        '''Start the worker threads'''
        
        try:
            for workerIndex in range(CRAWLER_DEFAULT_WORKERS):
                strWorkerName = "Worker " + str(workerIndex)
                worker = WorkerThread(self, strWorkerName)
                #worker.daemon = True
                worker.start()
                self.listworkers.append(worker)
        except Exception as e:
            print(" exception occured in crawler " + str(e))
            traceback.print_exc()
            exit()

    def crawl(self,urlObj):
        '''Main function to crawl URL's '''
        
        try:
            if ((urlObj.valid) and (urlObj.url not in CRAWLED_URLS.keys())):
                rsp = urlcon.urlopen(urlObj.url,timeout=2)
                hCode = rsp.read()
                soup = BeautifulSoup(hCode)
                links = self.scrap(soup)
                boolStatus = self.checkmax()
                if boolStatus:
                    CRAWLED_URLS.setdefault(urlObj.url,"True")
                else:
                    return
                for eachLink in links:
                    if eachLink not in VISITED_URLS:
                        parsedURL = urlparse(eachLink)
                        if parsedURL.scheme and "javascript" in parsedURL.scheme:
                            print("***************Javascript found in scheme " + str(eachLink) + "**************")
                            continue
                        if not parsedURL.scheme and not parsedURL.netloc:
                            print("No scheme and host found for "  + str(eachLink))
                            newURL = urlunparse(parsedURL._replace(**{"scheme":urlObj.scheme,"netloc":urlObj.netloc}))
                            eachLink = newURL
                        elif not parsedURL.scheme :
                            print("Scheme not found for " + str(eachLink))
                            newURL = urlunparse(parsedURL._replace(**{"scheme":urlObj.scheme}))
                            eachLink = newURL
                        print(" Found child link " + eachLink)
                        CRAWL_BUFFER.append(eachLink)
                        with self._lock:
                            self.count += 1
                            print(" Count is =================> " + str(self.count))
                        boolStatus = self.checkmax()
                        if boolStatus:
                            VISITED_URLS.setdefault(eachLink, "True")
                        else:
                            return
            else:
                print("Invalid URL or URL present in visited " + str(urlObj.url))
        except Exception as e:
            print("Unknown exception occured while fetching HTML code" + str(e))
            traceback.print_exc()

    def scrap(self,soup):
        '''Scrap all links from the soup object'''
        
        rec_links = []
        for link in soup.find_all('a'):
            rec_links.append(link.get('href'))
        return rec_links
    
    def checkmax(self):
        '''Check if Upper limit on URL's to be scrapped is reached'''
        
        boolStatus = True
        if MAX_COUNT_LIMIT and self.count >= MAX_COUNT_LIMIT:
            print(" Maximum count reached. Now exiting and stopping workers :( ")
            self.kill = True
            boolStatus = False
        return boolStatus

def saveDataToFile(listData):
    '''Save output data in a file under current directory'''
    
    pass

if __name__ == '__main__':
    try:
        if len(sys.argv) == 3:
            MAX_COUNT_LIMIT = int(sys.argv[2])
        CRAWL_BUFFER.append(str(sys.argv[1]))
        VISITED_URLS.setdefault(str(sys.argv[1]), "True")
        webC = WebCrawler()
        while webC.listworkers[0].is_alive():
            webC.listworkers[0].join(1)
    except KeyboardInterrupt:
        print("**************** Keyboard interrupt occured. Stopping all threads *******************")
        exit(0)
    except Exception as e:
        print("Unknown exception occured in main" + str(e))
        traceback.print_exc()
    finally:
        print("Number of URL's scrapped : " + str(len(VISITED_URLS)))
        print("================ VISITED URL's ==========================\n"+ str(VISITED_URLS) + "\n=======================================")
        saveDataToFile(VISITED_URLS.keys())
        webC.kill = True
