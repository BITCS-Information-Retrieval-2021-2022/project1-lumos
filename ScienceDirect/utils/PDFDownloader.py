import pymongo
import requests
import time
# from tqdm import tqdm
import config as config
# import LevelUrls as lu
# from ContentManager import ContentManager
import threadpool
# import os
import random
from GetProxy import getProxy
from selenium import webdriver


class PDFManager:
    '''
    爬取论文pdf
    '''
    database = config.db
    collection = "SciDirBasicInfo"

    def __init__(self):
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)
        self.pdfUrls = self.getPDFUrlsfromDB()
        random.shuffle(self.pdfUrls)

    def getPDFUrlsfromDB(self):
        db = self.client[self.database]
        col = db[self.collection]
        urls = col.find({"pdfVisit": False})
        urls = [url['pdf_url'] for url in urls]
        return urls

    def get_content(self, url):
        proxy = getProxy(random.randint(1, 5))
        while proxy is None:
            proxy = getProxy(random.randint(1, 5))
        try:
            user_agent = "Mozilla/5.0 (X11; Linux x86_64)" \
                         " AppleWebKit/537.36 (KHTML, like Gecko)" \
                         " Chrome/59.0.3071.109 Safari/537.36"
            response = requests.get(url, headers={'User-Agent': user_agent}, proxies=proxy)
            response.raise_for_status()  # 如果返回的状态码不是200， 则抛出异常;
            # 判断网页的编码格式， 便于respons.text知道如何解码;
            response.encoding = response.apparent_encoding
        except Exception:
            print("爬取错误")
        else:
            return response.content

    def reset(self):
        db = self.client[self.database]
        col = db[self.collection]
        col.update_many({}, {"$set": {"pdfVisit": False}})

    # 改过，加入了baseurl和proxy
    def downloadFile(self, url, fileName):
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                     " Chrome/59.0.3071.109 Safari/537.36"
        # url_ = url

        # proxy = getProxy(random.randint(1, 5))
        # while proxy is None:
        #     proxy = getProxy(random.randint(1, 5))
        # r = requests.get(url, headers={'User-Agent': user_agent}, stream=True, proxies=proxy)
        # while r is None:
        #     time.sleep(5)
        #     proxy = getProxy(random.randint(1, 5))
        #     r = requests.get(url, headers={'User-Agent': user_agent}, stream=True, proxies=proxy)

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--log-level=3')
        # pstr = str(self.proxy)
        # ppstr = pstr[10: len(pstr) - 2]
        # pppstr = ppstr.replace(':', '：')
        # chrome_options.add_argument('--proxy-server=https://' + pppstr)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            # print(i)
        url_new = driver.current_url
        driver.quit()

        r = requests.get(url_new, headers={'User-Agent': user_agent}, stream=True)

        # r = requests.get(url_, headers={'User-Agent': user_agent}, stream=True)
        print(r)
        str_r = str(r)
        time.sleep(1 + random.uniform(1, 3))
        if str_r == "<Response [403]>":
            time.sleep(3 + random.uniform(1, 2))
            return
        lenth = len(r.content)
        print(lenth)
        with open(fileName, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        self.updateBasicInfo(url, fileName)
        print("successful download pdf at: " + fileName)
        time.sleep(2 + random.uniform(1, 3))
        return

    def updateBasicInfo(self, url, filePath):
        '''
            已经爬过的pdf更新数据库的visit标记
        :param url:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        # pdfVisit标记设为true
        col.update_one({"pdf_url": url}, {"$set": {"pdfVisit": True}})
        # 更新paper信息中的pdf的文件路径
        col.update_one({"pdf_url": url}, {"$set": {"pdf_path": filePath}})

    # 新的run
    def run(self, poolSize=2):
        count = len(self.pdfUrls)
        print(count)
        # 构造线程参数
        args = []
        counts = 0
        for index in range(0, count):
            # if self.pdfUrls[index] == "" or "action" in self.pdfUrls[index]:
            if self.pdfUrls[index] == "":
                counts += 1
                continue
            print(self.pdfUrls[index])
            pdfurlSplit = self.pdfUrls[index].split("/")
            # print(pdfurlSplit)
            # fileName = pdfurlSplit[len(pdfurlSplit) - 1]
            # 改动，filename用的那一串数字
            fileName = pdfurlSplit[6] + ".pdf"
            # print(fileName)
            # 这里路径或许要换成绝对路径，相对不知道为啥找不到
            args.append((None, {'url': self.pdfUrls[index], "fileName": "D:/SciDirPdfs/" + fileName}))
        # a = 10 / 0
        # 线程池大小
        if count < poolSize:
            poolSize = count
        # 构造线程池
        print("wrong pdf num: " + str(counts))

        pool = threadpool.ThreadPool(poolSize)
        requests = threadpool.makeRequests(self.downloadFile, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()


if __name__ == '__main__':
    pdfManager = PDFManager()
    pdfManager.run()
    # pdfManager.reset()
