# import pymongo
import requests
from bs4 import BeautifulSoup
# from tqdm import tqdm
# import pdb
import os
import config
# import sys
# import datetime
import pymongo
# from SpringerContent import SpringerContent


def log(str):
    with open("../url.log", "a") as f:
        f.write(str)


class SpringerUrlsCrawler:
    database = config.db  # 爬取的url将要保存的数据库名
    collectionConferenceUrl = "SpringerConferenceUrls"  # 爬取的url将要保存的表名
    collectionJournalUrl = "SpringerJournalUrls"
    collectionConferenceSecondUrl = "SpringerConferenceSecondLevelUrls"
    collectionJournalSecondUrl = "SpringerJournalSecondUrls"

    def __init__(self):
        os.system('')
        self.baseUrl = "https://link.springer.com"
        self.paperUrl = []
        self.journalpaperUrl = []
        self.journalUrl = []
        self.paper_num = 0
        self.jounarl_num = 0
        self.conference_num = 0
        self.conferencepaperUrl = []
        self.conferenceUrl = []

        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)
        '''
             https://link.springer.com/ 为顶层
             https://link.springer.com/search?facet-discipline="Journal" Journal or Conference URL
             https://link.springer.com/article/10.1007/s41095-021-0235-7  具体论文url
        '''

    def hasSecondLevelUrlsInMongoDb(self, url, collection):
        db = self.client[self.database]
        col = db[collection]
        url_ = col.find({"url": url})
        count = 0
        for temp in url_:
            count += 1
        if count == 0:
            return False
        else:
            return True

    def saveUrlsToMongoDb(self, urls, collection):
        db = self.client[self.database]
        col = db[collection]
        Urls = []
        for url_ in urls:
            Urls.append({"url": url_, "visit": False})

        if len(Urls) == 0:
            return
        col.insert_many(Urls)

    def saveSecondLevelUrlsToMongoDb(self, url, collection):
        print("****")
        db = self.client[self.database]
        col = db[collection]
        col.insert_one({"url": url})

    def get_content(self, u):
        try:
            user_agent = 'Mozilla/5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) ' \
                         'Chrome/95.0.4638.69 Safari/537.36'
            response = requests.get(u, headers={'User-Agent': user_agent})
            # pdb.set_trace()
            response.raise_for_status()  # 如果返回的状态码不是200， 则抛出异常;
            response.encoding = response.apparent_encoding  # 判断网页的编码格式， 便于respons.text知道如何解码;

        except Exception:
            print("爬取错误")
        else:
            return response.content

    def getUrlsfromConference(self, conferencelevel: str):
        '''
        :param conferencelevel: conference url 获取paper url
        :return:
            成功返回 true,urls
            出错返回 false,[]
        '''
        Article_urls = []
        try:
            content = self.get_content(conferencelevel)
            soup = BeautifulSoup(content, 'html5lib')
            # print(soup)
            content_li = soup.find_all(name='div', attrs={'class': 'content-type-list__title'})
            # print('content_li',content_li)
            # 筛选Article的url
            for paper in content_li:
                paper_url = paper.find(name="a")['href']
                Article_urls.append(self.baseUrl + paper_url)

            self.conferencepaperUrl.extend(Article_urls)
            self.paper_num += len(Article_urls)
            print('paper url:', len(Article_urls), Article_urls)

            # get url from next page
            next_url = soup.find(name='a', attrs={'title': 'Next', 'rel': 'next'})['href']
            if next_url is not None:
                self.getUrlsfromConference(self.baseUrl + next_url)
            return True, Article_urls
        # except Exception as e:
            # lu.ErrorUrlManeger(domainlevel, e)
            print('getUrlsfromConference finished')
            return False, []

    def getUrlsfromJournal(self, journallevel: str):
        '''
        :param journallevel: journal url 领域搜索
                                https://link.springer.com/search?facet-content-type="Journal"
        :return:
            成功返回 true,urls
            出错返回 false,[]
        '''
        Article_urls = []
        try:
            content = self.get_content(journallevel)
            soup = BeautifulSoup(content, 'lxml')
            content_li = soup.find(name='ol', attrs={'id': 'results-list', 'class': 'content-item-list'}).find_all(
                name="li",
                attrs={"class": ""})
            # print('content_li',content_li)
            # 筛选Article的url
            for paper in content_li:
                str_p = str(paper.find(name='p', attrs={'class': 'content-type'}).text).strip()
                # print(str_p)
                if str_p == 'Article' or 'Chapter':
                    paper_url = paper.find(name="h2").find(name="a")['href']
                    Article_urls.append(self.baseUrl + paper_url)

            self.journalpaperUrl.extend(Article_urls)
            self.paper_num += len(Article_urls)
            print(self.paper_num)
            print('paper url:', len(Article_urls), Article_urls)

            # get url from next page
            next_url = soup.find(name='a', attrs={'class': 'next', 'title': 'next'})['href']
            if next_url is not None:
                result, paperUrl = self.getUrlsfromJournal(self.baseUrl + next_url)
                if result is True:
                    for url in paperUrl:
                        Article_urls.append(url)

            return True, Article_urls
        except Exception as e:
            # lu.ErrorUrlManeger(domainlevel, e)
            print('getUrlsfromJournal finished')
            return False, []

    def getUrlsJournalFinal(self, domainlevel: str):
        try:
            content = self.get_content(domainlevel)
            soup = BeautifulSoup(content, 'lxml')
            url_final = soup.find(name="a", attrs={'data-track-action': 'click view all articles'})['href']
            return True, url_final
        except Exception as e:
            print('getUrlsDomainFinal (view all article) failed:', domainlevel)
            return False, ""

    def getJournalfromTopLevel(self, toplevel: str):
        '''
        :param toplevel: 网站入口 https://link.springer.com
        https://link.springer.com/search?facet-content-type="Journal"
        https://link.springer.com/search?facet-content-type="ConferenceProceedings"
        :return:
        '''
        try:
            content = self.get_content(toplevel)
            soup = BeautifulSoup(content, 'lxml')

            tbodies = soup.find_all(name="li", attrs={'class': 'has-cover'})
            print("===========================================================")
            for domain in tbodies:
                domain_url = domain.find(name='h2').find(name="a")['href']
                print(self.baseUrl + domain_url)
                result, url_final = self.getUrlsJournalFinal(self.baseUrl + domain_url)
                if result is False:
                    continue
                if not self.hasSecondLevelUrlsInMongoDb(url_final, self.collectionJournalSecondUrl):
                    result, paperUrls = self.getUrlsfromJournal(url_final)
                    if result is False:
                        continue
                    self.saveUrlsToMongoDb(paperUrls, self.collectionJournalUrl)
                    log("total paper :{length}\n".format(length=len(paperUrls)))
                    self.saveSecondLevelUrlsToMongoDb(url_final, self.collectionJournalSecondUrl)
                    self.jounarl_num += len(paperUrls)

            next_url = soup.find(name='a', attrs={'class': 'next', 'title': 'next'})['href']
            if next_url is not None and self.jounarl_num < 20000:
                self.getJournalfromTopLevel(self.baseUrl + next_url)
            return True

        except Exception as e:
            # lu.ErrorUrlManeger(domainlevel, e)
            print('getJournal finished')
            return False

    def getConferencefromTopLevel(self, toplevel: str):
        '''
        :param toplevel: 网站入口
        https://link.springer.com/search?facet-content-type="ConferenceProceedings"
        :return:
        '''
        try:
            content = self.get_content(toplevel)
            soup = BeautifulSoup(content, 'lxml')

            tbodies = soup.find_all(name="li", attrs={'class': 'has-cover'})
            print("===========================================================")
            for domain in tbodies:
                domain_url = domain.find(name='h2').find(name="a")['href']
                print(self.baseUrl + domain_url)
                if not self.hasSecondLevelUrlsInMongoDb(self.baseUrl + domain_url, self.collectionConferenceSecondUrl):
                    log("=============================================================================\n")
                    log("Start downloading urls from : " + self.baseUrl + domain_url + "\n")
                    result, paperUrls = self.getUrlsfromConference(self.baseUrl + domain_url)
                    if result is False:
                        continue
                    self.saveUrlsToMongoDb(paperUrls, self.collectionConferenceUrl)
                    log("total paper :{length}\n".format(length=len(paperUrls)))
                    self.saveSecondLevelUrlsToMongoDb(self.baseUrl + domain_url, self.collectionConferenceSecondUrl)
                    self.conference_num += len(paperUrls)

            next_url = soup.find(name='a', attrs={'class': 'next', 'title': 'next'})['href']
            if next_url is not None and self.conference_num < 15000:
                self.getConferencefromTopLevel(self.baseUrl + next_url)
            return True

        except Exception as e:
            # lu.ErrorUrlManeger(domainlevel, e)
            print('getConference finished')
            return False


if __name__ == '__main__':
    url1 = 'https://link.springer.com/search?facet-content-type="ConferenceProceedings"'
    url2 = 'https://link.springer.com/search?facet-content-type="Journal"'
    springerCrawler = SpringerUrlsCrawler()
    springerCrawler.getConferencefromTopLevel(url1)
    springerCrawler.getJournalfromTopLevel(url2)
