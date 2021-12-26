import sys
import requests
from tqdm import tqdm  # noqa
from bs4 import BeautifulSoup
import datetime
import pymongo
import time
# import random

import config
# from GetProxy import getProxy

sys.path.append('./utils/')  # noqa


def log(str):
    with open("../basicInfo.log", "a") as f:
        f.write(str)


class SpringerContent:
    database = config.db  # 爬取的url将要保存的数据库名
    collectionConferenceUrl = "SpringerConferenceUrls"
    collectionJournalUrl = "SpringerJournalUrls"
    basicInfo = "SpringerBasicInfo"

    def __init__(self):
        super().__init__()
        self.baseUrl = "https://link.springer.com"

        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)

    def getUnvisitUrls(self, collection):
        db = self.client[self.database]
        col = db[collection]
        urls = col.find({"visit": False}, {"url": 1})
        urls = [url['url'] for url in urls]
        return urls

    def savePaperInfoToMongoDb(self, paperInfos):
        db = self.client[self.database]
        col = db[self.basicInfo]
        # 检查标题重复
        if col.find_one({"title": paperInfos["title"]}) is not None:
            return

        # todo: _id
        col.insert_one(paperInfos)

    def updateUrls(self, url, collection):
        db = self.client[self.database]
        col = db[collection]
        col.update_one({"url": url}, {"$set": {"visit": True}})

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

    def getContentfromConferencePaper(self, paperUrl: str):
        '''
        :param paperUrl: paper url
        :return: 返回paper 内容
        '''
        try:
            content = self.get_content(paperUrl)
            while content is None:
                time.sleep(10)
                content = self.get_content(paperUrl)
            soup = BeautifulSoup(content, 'lxml')
            content_li = soup.find(name="div", attrs={"class": "main-body"})

            authors = []
            # pdf_url = content_li.find(name='div', attrs={'c-pdf-download u-clear-both'}).find(name='a')['href']
            pdf_url = self.baseUrl + content_li.find(
                name='div', attrs={
                    'class': 'note test-pdf-link'
                }).find(name='a')['href']
            title = str(
                content_li.find(name='h1', attrs={
                    'class': 'ChapterTitle'
                }).text).strip()
            co_authors = content_li.find(name='ul',
                                         attrs={
                                             'class': 'test-contributor-names'
                                         }).find_all(name='span',
                                                     attrs={
                                                         'ite\
                                                                                                    mprop':
                                                         'name'
                                                     })
            for co_author in co_authors:
                # print(co_authors)
                author = str(co_author.text).strip()
                # print('author',author)
                authors.append(author)

            if content_li.find(name='section', attrs={'class': 'Abstract'
                                                      }) is not None:
                abstract = str(
                    content_li.find(name='section',
                                    attrs={
                                        'class': 'Abstract'
                                    }).find('p').text).strip()
            # print('Abstract:',abstract)
            pub_time = datetime.datetime.strptime(
                content_li.find(name='div', attrs={
                    'class': 'article-dates'
                }).find(name='time')['datetime'], '%Y-%m-%d')
            year = pub_time.year
            month = pub_time.month

            doi = content_li.find(name='span', attrs={
                'id': 'doi-url'
            }).text.strip()

            # type 会议或期刊
            type = 'conference'

            venue = str(
                content_li.find(name='a',
                                attrs={
                                    'data-track-action': 'Book title'
                                }).text).strip()  # 会议或期刊名
            # print('venue:',venue)
            outcite = content_li.find(name='ol',
                                      attrs={'class': 'BibliographyWrapper'})
            cites = outcite.find_all(name='li')
            outCitations = 0  # 引用论文数
            for c in cites:
                outCitations += 1

            source = 'Springer'  # 来源
            #  video_url = ''  # 视频链接
            # video_path = ''  # 视频保存路径
            # thumbnail_url = ''  # 视频略缩图链接
            # pdf_path = ''  # 下载到本地路径
            # inCitations = ''  # 被引数量

            return {
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "doi": doi,
                "paperUrl": paperUrl,
                "year": year,
                "month": month,
                "type": type,
                "venue": venue,
                "source": source,
                "video_url": "",  # 没这个
                "video_path": "",
                "thumbnail_url": "",
                "pdf_url": pdf_url,
                "pdf_path": "",
                "inCitations": "",
                "outCitations": outCitations,

                # 下面两个数据库不需要，拿出来方便下载
                "video_download": "",
                "pdf_download": pdf_url,

                # visited字段
                "pdfVisit": False,
                "videoVisit": False
            }
        except Exception as e:
            # lu.ErrorUrlManeger(paperUrl, e)
            print('getContentfromPaper failed:', paperUrl, e)
            return False

    def getContentfromJournalPaper(self, paperUrl: str):
        '''
        :param paperUrl: paper url 'https://link.springer.com/article/10.1007/s11634-020-00434-3'
        :return: 返回paper 内容
        '''
        try:
            content = self.get_content(paperUrl)
            while content is None:
                time.sleep(60)
                content = self.get_content(paperUrl)
            soup = BeautifulSoup(content, 'lxml')
            content_li = soup.find(
                name="main", attrs={"data-track-component": "article body"})

            authors = []

            pdf_url = content_li.find(name='div',
                                      attrs={'c-pdf-download u-clear-both'
                                             }).find(name='a')['href']
            # pdf_url = soup.find(name='meta', attrs={'name': 'citation_pdf_url'})['content']
            title = str(
                content_li.find(name='h1', attrs={
                    'class': 'c-article-title'
                }).text).strip()
            co_authors = content_li.find(
                name='ul', attrs={
                    'data-test': 'authors-list'
                }).find_all(name='a', attrs={'data-test': 'author-name'})
            for co_author in co_authors:
                # print(co_authors)
                author = str(co_author.text).strip()
                # print(author)
                authors.append(author)

            abstract = ""
            if content_li.find(name='div', attrs={'id': 'Abs1-content'
                                                  }) is not None:
                abstract = str(
                    content_li.find(name='div', attrs={
                        'id': 'Abs1-content'
                    }).find('p').text).strip()
            pub_time = datetime.datetime.strptime(
                content_li.find(name='ul',
                                attrs={
                                    'data-test': 'article-identifier'
                                }).find(name='time')['datetime'], '%Y-%m-%d')
            year = pub_time.year
            month = pub_time.month

            doi = content_li.find(name='ul', attrs={'data-test': 'publication-history'}).find(
                name='li', attrs={'class': 'c-bibliographic-in\\formati\\on__list-item \
                 c-bibliographic-information_list-item--doi'}) .find(name='a')['href']
            # type 会议或期刊
            type = 'journal'

            venue = str(
                content_li.find(name='i', attrs={
                    'data-test': 'journal-title'
                }).text).strip()  # 会议或期刊名
            outcite = content_li.find(name='ol',
                                      attrs={'class': 'c-article-references'})
            cites = outcite.find_all(name='li')
            outCitations = 0  # 引用论文数
            for c in cites:
                outCitations += 1

            source = 'Springer'  # 来源
            # video_url = ''  # 视频链接
            # video_path = ''  # 视频保存路径
            # thumbnail_url = ''  # 视频略缩图链接
            # pdf_path = ''  # 下载到本地路径
            # inCitations = ''  # 被引数量

            return {
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "doi": doi,
                "paperUrl": paperUrl,
                "year": year,
                "month": month,
                "type": type,
                "venue": venue,
                "source": source,
                "video_url": "",  # 没这个
                "video_path": "",
                "thumbnail_url": "",
                "pdf_url": pdf_url,
                "pdf_path": "",
                "inCitations": "",
                "outCitations": outCitations,

                # 下面两个数据库不需要，拿出来方便下载
                "video_download": "",
                "pdf_download": pdf_url,

                # visited字段
                "pdfVisit": False,
                "videoVisit": False
            }
        except Exception as e:
            # lu.ErrorUrlManeger(paperUrl, e)
            print(e)
            print('getContentfromPaper failed:', paperUrl)
            return False


if __name__ == '__main__':
    springerContent = SpringerContent()
    # urls2 = springerContent.getUnvisitUrls(springerContent.collectionJournalUrl)

    urls1 = springerContent.getUnvisitUrls(
        springerContent.collectionConferenceUrl)
    urls2 = springerContent.getUnvisitUrls(
        springerContent.collectionJournalUrl)

    print(len(urls1), len(urls2))

    log("Crawling from conference:\n")
    pbar = tqdm(urls1)
    for url_ in pbar:
        pbar.set_description("Crawling %s" % url_)
        paperInfo = springerContent.getContentfromConferencePaper(url_)
        if not paperInfo:
            print("----")
            continue
        springerContent.savePaperInfoToMongoDb(paperInfo)
        springerContent.updateUrls(url_,
                                   springerContent.collectionConferenceUrl)
        log("Paper *** " + url_ + " *** download.\n")

    log("\n")
    '''
    log("Crawling from journal:\n")
    pbar = tqdm(urls2)
    for url_ in pbar:
        pbar.set_description("Crawling %s" % url_)
        paperInfo = springerContent.getContentfromJournalPaper(url_)
        print(paperInfo)
        if not paperInfo:
            continue
        springerContent.savePaperInfoToMongoDb(paperInfo)
        #print("===")
        springerContent.updateUrls(url_, springerContent.collectionJournalUrl)
        log("Paper *** " + url_ + " *** download.\n")
    '''
