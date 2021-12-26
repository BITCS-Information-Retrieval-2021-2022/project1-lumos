import sys
import pymongo
import requests
from bs4 import BeautifulSoup
import config as config
from ACMUrlsCrawler import ACMUrlsCrawler
from GetProxy import getProxy
import random
from tqdm import tqdm
import time

sys.path.append('./utils/')


def log(str):
    with open("../basicInfo.log", "a") as f:
        f.write(str)
    f.close()


class ContentManager:
    '''
    爬取论文的基本内容
    '''
    database = config.db
    collection = "ACMBasicInfo"
    urlCollection = ACMUrlsCrawler.collection
    proxy = None

    def __init__(self):
        # self.database = database
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)

    def get_content(self, proxy, url):
        try:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                         " Chrome/96.0.4664.45 Safari/537.36"
            requests.packages.urllib3.disable_warnings()
            response = requests.get(url, headers={'User-Agent': user_agent}, proxies=proxy)
            # response = requests.get(url, headers={'User-Agent': user_agent})
            # response = requests.get(url, headers={'User-Agent': user_agent})

            # 如果返回的状态码不是200， 则抛出异常;
            response.raise_for_status()
            # 判断网页的编码格式， 便于respons.text知道如何解码;
            response.encoding = response.apparent_encoding
        except Exception:
            print()
            print("爬取错误")
            return None
        else:
            return response.content

    def parse(self, content, url):
        soup = BeautifulSoup(content, "lxml")
        # print(soup)

        title = ""
        title_soup = soup.find_all(name="h1", attrs={"class": "citation__title"})
        for t in title_soup:
            title = t.text

        abstract = ""
        abstract_soup = soup.find_all(name="div", attrs={"class": "abstractSection abstractInFull"})
        for ab in abstract_soup:
            if ab.find("p"):
                abstract = ab.find("p").text

        authors = []
        authors_soup = soup.find_all(name="div", attrs={"class": "author-data"})
        for au in authors_soup:
            # print(au)
            if au.find("span"):
                author = au.find("span").text
                authors.append(author)

        year = ""
        month = ""
        year_soup = soup.find_all(name="span", attrs={"class": "epub-section__date"})
        for y in year_soup:
            month = y.text.split(" ")[0]
            year = y.text.split(" ")[1]

        j_c = "journal"
        j_c_soup = soup.find_all(name="meta")
        # print(j_c_soup)

        for jc in j_c_soup:
            # print(jc)
            if "Conference" in jc:
                j_c = "conference"
                break
        # a = 10 / 0

        venue = ""
        venue_soup = soup.find_all(name="a", attrs={"class": "article__tocHeading"})
        for v in venue_soup:
            if " " in v.text:
                venue = v.text.split(" ")[0]
                break

        citations = ""
        citations_soup = soup.find_all(name="span", attrs={"class": "citation"})
        for c in citations_soup:
            for i in c.text:
                if i.isnumeric():
                    citations += i

        references = 0
        references_soup = soup.find_all(name="li", attrs={"class": "references__item"})
        for r in references_soup:
            references += 1

        video = ""
        video_soup = soup.find_all(name="div", attrs={"class": "cloudflare-stream-container"})
        for v in video_soup:
            if v.find("input"):
                video = v.find("input")['value']

        video_urls = []
        video_download = soup.find_all(name="div", attrs={"class": "video__links table__cell-view"})
        for vd in video_download:
            # print(vd.find(name="a", attrs={"title": "Download"})['href'])
            x = vd.find(name="a", attrs={"title": "Download"})['href']
            if x:
                if x != '#':
                    video_urls.append(x)

        pdf_download_url = ""
        pdf_download = soup.find_all(name="a", attrs={"class": "btn big stretched red"})
        for vd in pdf_download:
            pdf_download_url = vd['href']

        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "doi": url,
            "year": year,
            "month": month,
            "type": j_c,
            "venue": venue,
            "source": "ACM",
            "video_url": "",  # 没这个
            "video_path": "",
            "thumbnail_url": video,  # 可能没这个，随便扒了一个
            "pdf_url": pdf_download_url,
            "pdf_path": "",
            "inCitations": citations,
            "outCitations": references,

            # 下面两个数据库不需要，拿出来方便下载
            "video_download": video_urls,  # 返回的是列表，因为有可能好几个视频
            "pdf_download": pdf_download_url,

            # visited字段
            "pdfVisit": False,
            "videoVisit": False
        }

    def savePaperInfo(self, paperInfo):
        db = self.client[self.database]
        col = db[self.collection]
        # 检查标题重复
        if col.find_one({"title": paperInfo["title"]}) is not None:
            return

        # todo: _id
        col.insert_one(paperInfo)

    def updateUrl(self, url):
        '''
            已经爬过的url更新数据库的visit标记
        :param url:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.urlCollection]
        col.update_one({"url": url}, {"$set": {"visit": True}})
        # col.update_many({}, {"$set": {"visit": False}})

    def getUnvisitedUrls(self):
        '''
        获取之前爬取的未访问过的url
        :return:
        '''
        db = self.client[self.database]
        col = db[self.urlCollection]
        urls = col.find({"visit": False}, {"url": 1})
        urls = [url['url'] for url in urls]
        return urls

    def resetPDFUrls(self):
        db = self.client[self.database]
        col = db[self.collection]
        urls = col.find({}, {"url": 1})
        urls = [url['url'] for url in urls]
        for url in urls:
            url__ = 'https://dl.acm.org' + url
            col.update_one({"url": url}, {"$set": {"url": url__}})

    def run(self, url):
        '''
            爬取，保存并返回论文pdf url和视频 url
        :param url:
        :return:
        '''

        # proxy = getProxy(random.randint(1, 5))
        # while proxy is None:
        #     proxy = getProxy(random.randint(1, 5))
        while self.proxy is None:
            self.proxy = getProxy(random.randint(1, 5))
        content = self.get_content(self.proxy, url)

        doi_not_found = 0
        while content is None:
            doi_not_found += 1
            print("fail")
            time.sleep(5)
            self.proxy = getProxy(random.randint(1, 5))
            content = self.get_content(self.proxy, url)
            if doi_not_found > 25:
                print(url, " doi not found error")
                log(url + " doi not found error")
                self.updateUrl(url)
                return
        paperInfo = self.parse(content, url)
        self.savePaperInfo(paperInfo)
        self.updateUrl(url)
        log("Paper *** " + url + " *** download.\n")
        return paperInfo['pdf_download'], paperInfo['video_download']


if __name__ == "__main__":

    contentManager = ContentManager()
    Urls = contentManager.getUnvisitedUrls()

    p = 1
    pbar = tqdm(Urls)
    for url_ in pbar:
        url = url_
        if "acm" not in url_:
            url = "https://dl.acm.org/doi" + url_[15:]
        pbar.set_description("Crawling %s" % url)
        contentManager.run(url_)
        if p % 500 == 0:
            time.sleep(300)
        if p % 2000 == 0:
            time.sleep(300)
        p += 1
