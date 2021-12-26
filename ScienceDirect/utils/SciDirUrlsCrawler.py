import pymongo
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm import tqdm
# import pdb
import os
import config as config
import LevelUrls as lu
# import sys
import time
import GetProxy as GetProxy
import random


def log(str):
    with open("url.log", "a") as f:
        f.write(str)


class SciDirUrlsCrawler:
    database = config.db  # 爬取的url将要保存的数据库名
    collection = "SciDirUrls"  # 爬取的url将要保存的表名

    # finishflag = "finish"  # 爬取url结束后保存的表名，有内容表明可以直接从数据库中读，否则爬取url

    def __init__(self):
        os.system('')
        self.baseUrl = "https://www.sciencedirect.com"
        self.proxy = GetProxy.getProxy(0)
        '''
        约定 https://www.sciencedirect.com/browse/journals-and-books?contentType=JL 为顶层
             https://www.sciencedirect.com/journal/aace-clinical-case-reports 为2级
             https://www.sciencedirect.com/journal/aace-clinical-case-reports/articles-in-press 为1级
             https://www.sciencedirect.com/science/article/pii/S2376060521001243 为0级
        '''
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)

    def get_content_dynamic(self, u):
        proxy = GetProxy.getProxy(random.randint(1, 5))
        while proxy is None:
            proxy = GetProxy.getProxy(random.randint(1, 5))
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--log-level=3')
        pstr = str(proxy)
        ppstr = pstr[10:len(pstr) - 2]
        pppstr = ppstr.replace(':', '：')
        chrome_options.add_argument('--proxy-server=https://' + pppstr)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(u)
        for i in range(3):
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
        html = driver.page_source
        driver.quit()
        # print(html)
        return html

    def get_content(self, u):
        try:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                         " Chrome/96.0.4664.45 Safari/537.36"
            response = requests.get(u, headers={'User-Agent': user_agent})
            # pdb.set_trace()
            response.raise_for_status()  # 如果返回的状态码不是200， 则抛出异常;
            response.encoding = response.apparent_encoding  # 判断网页的编码格式， 便于respons.text知道如何解码;

        except Exception:
            print("爬取错误")
            return None
        else:
            # print(response.url)
            return response.content

    def getSciDirUrls(self):
        print("start to crawl paper urls...")
        self.getUrlsfromTopLevel(self.baseUrl + "//browse/journals-and-books?contentType=JL")
        print("urls downloading done")
        return

    def getUrlsfromFirstLevel(self, firstlevel: str):
        '''
        约定 https://www.sciencedirect.com/browse/journals-and-books?contentType=JL 为顶层
             https://www.sciencedirect.com/journal/aace-clinical-case-reports 为2级
             https://www.sciencedirect.com/journal/aace-clinical-case-reports/articles-in-press 为1级
             https://www.sciencedirect.com/science/article/pii/S2376060521001243 为0级
        '''
        print("firstlevel", firstlevel)

        try:
            content = self.get_content(firstlevel)
            soup = BeautifulSoup(content, 'lxml')
            papers = soup.find_all(
                name="a",
                attrs={
                    "class":
                    "anchor article-content-title u-margin-xs-top u-margin-s-bottom"
                })
            paperUrls = []
            for paper in papers:
                paperUrl = paper["href"]
                # print(paperUrl)
                paperUrls.append(self.baseUrl + paperUrl)

            # 处理多页情况
            i = 1
            while i < 10:
                i += 1
                temp = firstlevel + "?page=" + str(i)
                content_temp = self.get_content(temp)
                if content_temp is []:
                    break
                soup_temp = BeautifulSoup(content_temp, 'lxml')
                papers_temp = soup_temp.find_all(
                    name="a",
                    attrs={
                        "class":
                        "anchor article-content-title\
                                                          u-margin-xs-top u-margin-s-bottom"
                    })
                for paper_temp in papers_temp:
                    paperUrl_temp = paper_temp["href"]
                    paperUrls.append(self.baseUrl + paperUrl_temp)

            return paperUrls
        except Exception as e:
            lu.ErrorUrlManeger(firstlevel, e)
            return []

    def getUrlsfromSecondLevel(self, secondlevel: str):
        '''
        约定 https://www.sciencedirect.com/browse/journals-and-books?contentType=JL 为顶层
             https://www.sciencedirect.com/journal/aace-clinical-case-reports 为2级
             https://www.sciencedirect.com/journal/aace-clinical-case-reports/articles-in-press 为1级
             https://www.sciencedirect.com/science/article/pii/S2376060521001243 为0级
        '''
        print("secondlevel", secondlevel)

        paperUrls = []
        FirstLevelUrls = []

        try:
            content = self.get_content(secondlevel)
            soup = BeautifulSoup(content, 'lxml')

            FirstUrl = soup.find_all(
                name="a",
                attrs={
                    "class":
                    "button-alternative js-listing-link button-alternative-primary"
                })
            for f_u in FirstUrl:
                url_temp = f_u['href']
                FirstLevelUrls.append(self.baseUrl + url_temp)

            pbar = tqdm(FirstLevelUrls)
            for FirstLevelUrl in pbar:
                pbar.set_description("Crawling %s" % FirstLevelUrl)
                partUrls = self.getUrlsfromFirstLevel(FirstLevelUrl)
                log("\t" + FirstLevelUrl + ":" + str(len(partUrls)) + "\n")
                paperUrls += partUrls
            # print(paperUrls)
            return True, paperUrls
        except Exception as e:
            print(e)
            return False, []

    def getUrlsfromTopLevel(self, toplevel: str):
        '''
        约定 https://www.sciencedirect.com/browse/journals-and-books?contentType=JL 为顶层
             https://www.sciencedirect.com/journal/aace-clinical-case-reports 为2级
             https://www.sciencedirect.com/journal/aace-clinical-case-reports/articles-in-press 为1级
             https://www.sciencedirect.com/science/article/pii/S2376060521001243 为0级
        '''
        print("toplevel", toplevel)
        secondLevelManager = lu.SecondLevelManager()

        i = 1
        while i:
            print("i:" + str(i))
            temp_url = "https://www.sciencedirect.com/browse/journals-and-books?page=" + str(
                i) + "&contentType=JL"
            content = self.get_content(temp_url)
            if content is []:
                break
            soup = BeautifulSoup(content, 'lxml')

            SecondUrl = soup.find_all(
                name="a", attrs={"class": "anchor js-publication-title"})

            for s_url in SecondUrl:
                try:
                    url_temp = s_url['href']
                    url_ = self.baseUrl + url_temp
                    print(url_)
                    if not secondLevelManager.hasInMongoDb(url_):
                        log("=============================================================================\n"
                            )
                        log("Start downloading urls from : " + url_ + "\n")
                        result, partUrls = self.getUrlsfromSecondLevel(url_)
                        # print(partUrls)
                        if result is False:
                            continue
                        self.saveUrls(partUrls)
                        log("total paper :{length}\n".format(
                            length=len(partUrls)))
                        secondLevelManager.saveSecondLevelUrls(url_)
                    else:
                        print("has in mongodb")
                except Exception as e:
                    print(e)
                    pass

            i += 1

        log("total paper in site:{length}\n".format(
            length=len(self.getAllUrls())))

    def saveUrls(self, urls):
        '''
        保存爬取的url
        :param urls:
        :return:
        '''

        db = self.client[self.database]
        col = db[self.collection]
        urlsInDB = col.find({}, {"url": 1})
        urlsInDB = [urls['url'] for urls in urlsInDB]

        Urls = []
        for url in urls:
            if (url in urlsInDB):
                # 去重
                continue
            else:
                Urls.append({"url": url, "visit": False})
        if (len(Urls) == 0):
            return
        col.insert_many(Urls)

    def getAllUrls(self):
        '''
            获取数据库中所有的url
            :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        urls = col.find({}, {"url": 1})
        urls = [url['url'] for url in urls]
        return urls

    def updateUrl(self, url):
        '''
            已经爬过的url更新数据库的visit标记
        :param url:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        col.update_one({"url": url}, {"$set": {"visit": True}})


if __name__ == '__main__':
    SciDirCrawler = SciDirUrlsCrawler()
    SciDirCrawler.getSciDirUrls()
