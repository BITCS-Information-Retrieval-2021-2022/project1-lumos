# mport sys
import pymongo
import requests
from bs4 import BeautifulSoup
import config as config
from SciDirUrlsCrawler import SciDirUrlsCrawler
from GetProxy import getProxy
import random
import time
from tqdm import tqdm
from selenium import webdriver


def log(str):
    with open("../basicInfo.log", "a") as f:
        f.write(str)
    f.close()


class ContentManager():
    '''
    爬取论文的基本内容
    '''
    database = config.db
    collection = "SciDirBasicInfo"
    urlCollection = SciDirUrlsCrawler.collection
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
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                         " Chrome/59.0.3071.109 Safari/537.36"
            requests.packages.urllib3.disable_warnings()
            response = requests.get(url, headers={'User-Agent': user_agent}, proxies=proxy)
            # 如果返回的状态码不是200， 则抛出异常;
            response.raise_for_status()
            # 判断网页的编码格式， 便于respons.text知道如何解码;
            response.encoding = response.apparent_encoding
        except Exception:
            print(url + "   爬取错误")
            return None
        else:
            return response.content

    def parse(self, content, paper_url):
        soup = BeautifulSoup(content, 'lxml')

        # title
        # title = soup.title.string
        title = ""
        if soup.find_all(name="span", attrs={"class": "title-text"}):
            title_soup = soup.find_all(name="span", attrs={"class": "title-text"})
            for t in title_soup:
                title = t.text
        # print(title)

        # abstract
        abstract = ""
        if soup.find(name="div", attrs={"class": "abstract author"}):
            abstract_block = soup.find(name="div", attrs={"class": "abstract author"})
            # print(abstract_block)
            if abstract_block.find_all("div"):
                abstracts = abstract_block.find_all("div")
                for i in abstracts:
                    if i.find("h3"):
                        abstract += i.find("h3").text
                        abstract += "\n"
                    if i.find("p"):
                        abstract += i.find("p").text
                        abstract += "\n"
        # print("abstract:\n")
        # print(abstract)

        # author
        citation_author_given_name = soup.find_all(name="span", attrs={"class": "text given-name"})
        citation_author_surname = soup.find_all(name="span", attrs={"class": "text surname"})
        citation_authors = []
        for i in range(0, len(citation_author_given_name)):
            try:
                temp = ""
                temp += citation_author_given_name[i].text
                temp += " "
                temp += citation_author_surname[i].text
                # print(temp)
                citation_authors.append(temp)
            except Exception:
                pass

        # doi
        # paperUrl = paper.find(name="dt").find("a")["href"]
        doi = ""
        if soup.find(name="a", attrs={"class": "doi"}):
            doi = soup.find(name="a", attrs={"class": "doi"}).text
        print(doi)

        # url
        url = paper_url

        # year
        # month
        paper_time = soup.find(name="div", attrs={"class": "text-xs"})
        if paper_time:
            paper_time = paper_time.text
        # print(paper_time)
        MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"]
        count = []
        paper_time_split = paper_time.split(" ")
        for temp in paper_time_split:
            if ',' in temp:
                split_new = temp.split(',')
                for strstr in split_new:
                    count.append(strstr)
            else:
                count.append(temp)
        # print(count)
        year = ""
        month = ""
        for i in count:
            if i in MONTH:
                month = i
                print(month)
            elif len(i) == 4 and i < "2022":
                year = i
                print(year)

        # type
        type = "journal"

        # venue
        # publication-title-link
        venue = soup.find(attrs={"class": "publication-title-link"}).text
        print(venue)

        # source
        source = "ScienceDirect"

        # pdf_url
        pdfurls = soup.find_all(name="a", attrs={"class": "link-button link-button-primary accessbar-primary-link"})
        # print(pdfurls)
        pdfurl = ""
        for a in pdfurls:
            if a.attrs['href']:
                pdfurl = "https://www.sciencedirect.com" + a['href']
                print(pdfurl)

        # pdf_path

        # inCitations 被引数量
        inCitationsstr = soup.find_all(name="h2", attrs={"class": "section-title u-h4"})
        # cnt = 0
        inCitations = 0
        for i in inCitationsstr:
            if "Citing" in i.string:
                print(i.string)
                str = i.string
                sstr = str.split('(')
                ssstr = sstr[1].split(')')
                inCitations = ssstr[0]
                print(inCitations)
                break

        # outCitations 引用论文数量
        outCite = soup.find_all(name="dd", attrs={"class": "reference"})
        # print(len(outCite))
        outCitations = len(outCite)
        print(outCitations)

        return {
            "title": title,
            "authors": ", ".join(citation_authors),
            "abstract": abstract,
            "doi": doi,
            "url": url,
            "year": year,
            "month": month,
            "type": type,
            "venue": venue,
            "source": source,
            "pdf_url": pdfurl,
            "pdf_path": "",
            "video_url": "",
            "video_path": "",
            "thumbnail_url": "",
            "inCitations": inCitations,
            "outCitations": outCitations,

            # 数据库不需要
            "pdf_download": pdfurl,
            "pdfVisit": False
        }

    def savePaperInfo(self, paperInfo):
        db = self.client[self.database]
        col = db[self.collection]
        # 检查标题重复
        if (col.find_one({"title": paperInfo["title"]}) is not None):
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

    def reset_id(self):
        db = self.client[self.database]
        col = db[self.collection]
        paperInfo = col.find()
        id = 1
        for paper in paperInfo:
            # print(paper)
            # pdb.set_trace()
            col.update_one({"_id": paper['_id']}, {"$set": {"_id": id}})
            id += 1
        # print(paperInfo[0])

    def run(self, url):
        '''
            爬取，保存并返回论文pdf url和视频 url
        :param url:
        :return:
        '''
        while self.proxy is None:
            self.proxy = getProxy(random.randint(1, 5))
        content = self.get_content(self.proxy, url)

        doi_not_found = 0
        # print("content is ", content)
        while content is None:
            doi_not_found += 1
            # print("fail, content is ---------------------", content)
            time.sleep(5)
            self.proxy = getProxy(random.randint(1, 5))
            content = self.get_content(self.proxy, url)
            if doi_not_found > 50:
                print(url, " doi not found error")
                log(url + " doi not found error")
                # self.updateUrl(url)
                return

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--log-level=3')
        pstr = str(self.proxy)
        ppstr = pstr[10: len(pstr) - 2]
        pppstr = ppstr.replace(':', '：')
        chrome_options.add_argument('--proxy-server=https://' + pppstr)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            # print(i)
        html = driver.page_source
        # print(html)

        # time.sleep(30)

        # pdf = driver.find_element_by_link_text('View PDF')
        # pdf.click()

        # incite = driver.find_elements_by_class_name('u-h4')
        # # t.sleep(30)
        # # print("incite!!!!!!!!!!!!!!!")
        # for i in incite:
        #     if "Citing" in i.text:
        #         print(i.text)
        #         str = i.text
        #         sstr = str.split('(')
        #         ssstr = sstr[1].split(')')
        #         cite = ssstr[0]
        #         break

        # ref = driver.find_elements_by_class_name('reference')
        # # print(len(ref))
        # outCitations = len(ref)

        # time.sleep(30)

        # driver.switch_to.window(driver.window_handles[1])
        # print(driver.current_url)
        # pdfurl = driver.current_url
        driver.quit()

        paperInfo = self.parse(html, url)
        print("====================================================================================")
        print(paperInfo)
        print("====================================================================================")
        self.updateUrl(url)
        self.savePaperInfo(paperInfo)
        return paperInfo['pdf_download']


if __name__ == "__main__":
    contentManager = ContentManager()
    Urls = contentManager.getUnvisitedUrls()
    # Urls = ["https://www.sciencedirect.com/science/article/pii/S2376060521001243",
    #  "https://www.sciencedirect.com/science/article/pii/S2352940718302853"]

    p = 1
    pbar = tqdm(Urls)
    for url_ in pbar:
        pbar.set_description("Crawling %s" % url_)
        contentManager.run(url_)
        if p % 500 == 0:
            time.sleep(300)
        if p % 2000 == 0:
            time.sleep(300)
        p += 1
