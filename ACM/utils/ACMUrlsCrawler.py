import pymongo
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from tqdm import tqdm
# import ClashControl as cc
# import pdb
import os
import config as config
import LevelUrls as lu
# import GetProxy


def log(str):
    with open("../url.log", "a") as f:
        f.write(str)


class ACMUrlsCrawler:
    database = config.db  # 爬取的url将要保存的数据库名
    collection = "ACMUrls"  # 爬取的url将要保存的表名

    def __init__(self):
        os.system('')
        # self.baseUrl = "https://www.aclweb.org"
        self.baseUrl = "https://dl.acm.org/"
        self.baseUrl_ = "https://dl.acm.org"

        # db
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)

    # 下面7个函数是通用函数
    def resetVisitUrls(self):
        db = self.client[self.database]
        col = db[self.collection]
        col.update_many({}, {"$set": {"visit": False}})

    def getUnvisitedUrls(self):
        '''
        获取数据库中已保存且未爬取的url
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        urls = col.find({"visit": False}, {"url": 1})
        urls = [url['url'] for url in urls]
        return urls

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

    def deleteUrls(self, urls):
        db = self.client[self.database]
        col = db[self.collection]
        for url in urls:
            col.delete_one({"url": url})

    def getNextPageAndPapers(self, cururl: str):
        content = self.get_content(cururl)
        if content == 0:
            return [], []
        cursoup = BeautifulSoup(content, 'lxml')
        nextpage = cursoup.find_all(name="a",
                                    attrs={"class": "pagination__btn--next"})
        curpage = cursoup.find_all(
            name="a", attrs={"class": "issue-item__doi dot-separator"})
        nextpageUrl = []
        paperUrls = []
        for cur in curpage:
            paperUrl = cur['href']  # 找到proceeding的url
            paperUrls.append(paperUrl)
        for n in nextpage:
            nextpageUrl = n['href']

        return nextpageUrl, paperUrls

    def getNextPageAndProceedings(self, cururl: str):
        content = self.get_content(cururl)
        if content == 0:
            return [], []
        cursoup = BeautifulSoup(content, 'lxml')
        nextpage = cursoup.find_all(name="a",
                                    attrs={"class": "pagination__btn--next"})
        curpage = cursoup.find_all(name="div",
                                   attrs={"class": "issue-item__content"})
        nextpageUrl = []
        proceedingUrls = []
        for cur in curpage:
            proceedingUrl = cur.find(name="a")['href']  # 找到proceeding的url
            proceedingUrls.append(proceedingUrl)
        for n in nextpage:
            nextpageUrl = n['href']

        return nextpageUrl, proceedingUrls

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
            return 0
        else:
            # print(response.url)
            return response.content

    '''
    因为 ACM 网站是动态网站，所以借用谷歌浏览器的驱动插件来实现模拟人滑动浏览器，等到网页全部加载出来，再爬取里面的内容，如此就不会
    导致爬取的内容缺失
    '''
    def get_content_dynamic(self, u):
        driver = webdriver.Chrome()
        driver.get(u)
        # print("&&&&&&&&&&&&&&&&&&&&")
        for i in range(6):
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(10)
            # print(i)
        html = driver.page_source
        return html

    # 下面4个函数是层级调用
    def saveUrlToMongoDb(self):
        # self.getUrlsFromTopLevel(self.baseUrl + "journals/")
        self.getUrlsFromTopLevel(self.baseUrl + "browse/")

    def getUrlsFromTopLevel(self, toplevel: str):
        print("toplevel", toplevel)
        secondLevelManager = lu.SecondLevelManager()
        # SecondLevelUrls = []
        '''
        journals 和 browse 两种类型的论文爬取方式不太一样
        journals 类型的论文总共有63个二级页面，所以以一个二级页面为分界，爬取该二级页面下的所有论文的url，然后存储到数据库中，同时
        把该二级页面的url存储到数据库中，如此就可以保证程序中断后重新开始爬虫时，可以跳过这个爬取过的二级页面
        browse 类型的论文以一个期刊的一个翻页为分界，一般一个翻页里有20篇论文，爬取这20篇论文的url并存储到数据库中，同时把该二级页
        面的url存储到数据库中，如此就可以保证断点续爬
        '''
        if "journals" in toplevel:
            content = self.get_content_dynamic(toplevel)
            soup = BeautifulSoup(content, 'lxml')
            # print(soup)
            journalUrls = soup.findAll(name="div",
                                       attrs={"class": "browse-item-body"})
            # print(journalUrls)
            pbar = tqdm(journalUrls)
            for journal in pbar:
                pbar.set_description("Crawling %s" % journal)
                try:
                    # 这里获取了譬如https://dl.acm.org/journal/dtrap
                    url_ = self.baseUrl + journal.find(name="a")['href']
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
                except Exception as e:
                    print(e)
                    pass
        elif "browse" in toplevel:
            content = self.get_content(toplevel)
            soup = BeautifulSoup(content, 'lxml')
            proceedingUrls = soup.find_all(name="a",
                                           attrs={
                                               "class":
                                               "acm-browse__item-footer",
                                               "title": "Proceedings"
                                           })
            # print(proceedingUrls)
            try:
                # 这里获取了 https://dl.acm.org/browse/proceeding
                url_ = self.baseUrl_ + proceedingUrls[0]['href']
                print(url_)
                self.getUrlsfromSecondLevel(url_)
            except Exception:
                pass

        log("total paper in site:{length}\n".format(
            length=len(self.getAllUrls())))

    def getUrlsfromSecondLevel(self, secondlevel: str):
        paperUrls = []
        FirstLevelUrls = []
        print("secondlevel", secondlevel)
        if "journal" in secondlevel:
            try:
                # content = self.get_content(secondlevel)
                # soup = BeautifulSoup(content, 'lxml')
                # 比较耍赖的方法，后续会改
                journal_name = ""
                for i in range(len(secondlevel)):
                    if secondlevel[len(secondlevel) - i - 1] == '/':
                        break
                    journal_name += secondlevel[len(secondlevel) - i - 1]
                journal_name = journal_name[::-1]
                # all_downloads = soup.find_all(name="a", attrs={"class": "toc-badge__view-all"})
                all_downloads = "https://dl.acm.org/action/doSearch?SeriesKey=" + journal_name + "&sortBy=downloaded"
                # for ad in all_downloads:
                #     articles = issue['href']
                #     FirstLevelUrls.append(self.baseUrl + articles)
                FirstLevelUrls.append(all_downloads)

                pbar = tqdm(FirstLevelUrls)
                for FirstLevelUrl in pbar:
                    pbar.set_description("Crawling %s" % FirstLevelUrl)
                    partUrls = self.getUrlsfromFirstLevel(FirstLevelUrl)
                    log("\t" + FirstLevelUrl + ":" + str(len(partUrls)) + "\n")
                    paperUrls += partUrls
                # print(paperUrls)
                return True, paperUrls
            except Exception:
                return False, 0

        elif "proceeding" in secondlevel:
            try:
                nextUrl, proceedingUrls = self.getNextPageAndProceedings(
                    secondlevel)
                # print("----" + nextUrl)
                # 获取如https://dl.acm.org/doi/proceedings/10.1145/3479986
                secondLevel = lu.SecondLevelManager()
                '''
                这里全搞错了，还需要把数据库中的内容都删除。。。。。。
                网站的层次结构搞错了。。。。。。
                secondlevel 对应的是20篇期刊的页面，期刊才是要存的二级url
                '''
                for purls in proceedingUrls:
                    url_ = self.baseUrl_ + purls
                    if not secondLevel.hasInMongoDb(url_):
                        log("=============================================================================\n"
                            )
                        log("Start downloading urls from : " + url_ + "\n")
                        print("Start downloading urls from : " + url_)
                        paperUrls = self.getUrlsfromFirstLevel(url_)
                        print(paperUrls)
                        self.saveUrls(paperUrls)
                        secondLevel.saveSecondLevelUrls(url_)
                        log("total paper :{length}\n".format(
                            length=len(paperUrls)))

                while nextUrl:
                    n, p = self.getNextPageAndProceedings(nextUrl)
                    for ip in p:
                        ip_ = self.baseUrl_ + ip
                        if not secondLevel.hasInMongoDb(ip_):
                            log("=============================================================================\n"
                                )
                            log("Start downloading urls from : " + ip_ + "\n")
                            print("Start downloading urls from : " + ip_)
                            paperUrls = self.getUrlsfromFirstLevel(ip_)
                            self.saveUrls(paperUrls)
                            secondLevel.saveSecondLevelUrls(ip_)
                            log("total paper :{length}\n".format(
                                length=len(paperUrls)))
                    nextUrl = n

                return True
            except Exception:
                return False

    def getUrlsfromFirstLevel(self, firstlevel: str):
        print("firstlevel", firstlevel)
        if "proceedings" in firstlevel:
            try:
                content = self.get_content(firstlevel)
                soup = BeautifulSoup(content, 'lxml')
                papers = soup.find_all(
                    name="div", attrs={"class": "issue-item__content-right"})
                # 论文页面 https://dl.acm.org/doi/10.1145/3412569.3412575
                paperUrls = []
                # print("****")
                for paper in papers:
                    paperUrl = paper.find(name="a")["href"]
                    paperUrls.append(self.baseUrl_ + paperUrl)
                return paperUrls
            except Exception:
                return []
        else:
            try:
                nextUrl, articleUrls = self.getNextPageAndPapers(firstlevel)
                # 论文页面 https://dl.acm.org/doi/10.1145/3427097
                paperUrls = []
                for aurls in articleUrls:
                    paperUrls.append(aurls)
                while nextUrl:
                    n, a = self.getNextPageAndPapers(nextUrl)
                    for ia in a:
                        paperUrls.append(ia)
                    nextUrl = n
                # print("paper", paperUrls)
                return paperUrls
            except Exception:
                return []


if __name__ == "__main__":
    acmUrlCrawler = ACMUrlsCrawler()
    acmUrlCrawler.saveUrlToMongoDb()
    # acmUrlCrawler.resetVisitUrls()
