import pymongo
import requests
import threadpool
# from tqdm import tqdm
import config as config
import time
# from multiprocessing.dummy import Pool
import random
# import urllib.request


class PDFManager():
    '''
    爬取论文pdf
    '''
    database = config.db
    collection = "SpringerBasicInfo"

    # paper = ContentManager.collection

    def __init__(self):
        # self.database = "ACLAnthology"

        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)
        self.pdfUrls = self.getPDFUrlsfromDB()
        self.pdfUrlsUseful = []

    def getPDFUrlsfromDB(self):
        db = self.client[self.database]
        col = db[self.collection]
        return [url['pdf_download'] for url in col.find({"pdfVisit": False})]

    def get_content(self, url):
        try:
            user_agent = "Mozilla/5.0 (X11; Linux x86_64)" \
                         " AppleWebKit/537.36 (KHTML, like Gecko)" \
                         " Chrome/59.0.3071.109 Safari/537.36"
            response = requests.get(url, headers={'User-Agent': user_agent})
            response.raise_for_status()  # 如果返回的状态码不是200， 则抛出异常;
            # 判断网页的编码格式， 便于respons.text知道如何解码;
            response.encoding = response.apparent_encoding
        except Exception:
            print("爬取错误")
        else:
            return response.content

    # 改过，加入了baseurl和proxy
    def downloadFile(self, url, fileName):
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                     " Chrome/59.0.3071.109 Safari/537.36"

        cookie_copy_from_web = 'idp_marker=8e0c065c-3222-4846-a4a4-e5915fa922b7;\
        OptanonAlertBoxClosed=2021-11-01T07:29:10.889Z; _ga=GA1.2.1695484166.1635751751; \
        permutive-id=8efad603-1257-48a3-9324-1b74bf4da263;\
             __gads=ID=0904beb04aaa075d-227d78a77dce00cf:T=1635751753:S=ALNI_Mbrb7m9uHZsnnzAv1frWjxnd2VCBQ;\
                  _uetvid=1fb39c0049ef11ecb0b0cdf7dd86a8b4; Hm_lvt_92dc0ba795afae15bcf\
                      6ac1d3276202e=1637410286,1637499346,1637989794,1638076157;\
                       _fbp=fb.1.1638076884334.695362321; cto_bundle=yDyTC19GTnBHYnlwdEhyVExVWG8lMkY\
                           xRElSN0p3UXE0NWRjU1l6ZUZJNlp6JTJGJTJGTFRrS2tlJTJ\
                           GemtYd3UzeEd1aTJoNnBLZk82bDF2cU9RN3VsJTJGaHJjUmlVZU53UjZHRXRFWE\
                               hESSUyRkhvSzBPekE3dUJJT3p3JTJCajZSOW5tdUpuOG9qOEE1eHI3T1ZVT\
                               E85R1dUWVQzV0ZnOUVUTGZoUSUzRCUzRA; OptanonConsent=isIABG\
                                   lobal=false&datestamp=Sun+Nov+28+2021+15%3A52%3A39+GMT%2B0800\
                                   +(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=6.12.0&hosts=&landingPath=NotLandingPag\
                                       e&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0005%3A1%2CC0008%3A1%2CC0009%3A1%2Cgad%3A1&\
                                           geolocation=%3B&AwaitingReconsent=false; permutive-session=%7B%22session\
                                               _id%22%3A%222c734ae7-2f56-4652-868d-ad1172f24ea2%22%2C%22last_updated%22%3A%22202\
                                                   1-11-28T07%3A52%3A40.491Z%22%7D; tr\
                                                       ackid=ca93cca5035a404680faa1425; idp_sessio\
                                                       n=sVERSION_13e885d12-b77a-4251-\
                                                           b661-bbbdce217474; idp_session_http=hVERSION_1ce7\
                                                           9fa9d-fa2f-4032-8078-0c27\
                                                               849a9227; sim-inst-token=1::1639252759517:de6a3ff3'

        # cookie = cookiejar.MozillaCookieJar()
        # # 从文件中读取cookie内容到变量
        # cookie.load('cookie.txt', ignore_discard=True, ignore_expires=True)
        # 创建请求的request
        # req = urllib.request.Request("http://www.baidu.com")
        # 利用urllib2的build_opener方法创建一个opener
        # opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie))
        # response = opener.open(req)
        # print
        # cookie=response.read()
        # print(cookieStr)
        '''
        print("url", url)
        print(cookie_copy_from_web)
        '''
        r = requests.get(url,
                         headers={
                             'User-Agent': user_agent,
                             'cookie': cookie_copy_from_web
                         },
                         stream=True,
                         allow_redirects=False)
        print(r)
        str_r = str(r)
        time.sleep(1 + random.uniform(1, 3))
        if str_r == "<Response [403]>":
            time.sleep(3 + random.uniform(1, 2))
            return
        lenth = len(r.content)
        print(lenth)

        if lenth > 2e5:
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
        :param filePath:
        :param url:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        # visit标记设为true
        col.update_one({"pdf_url": url}, {"$set": {"pdfVisit": True}})
        # 更新paper信息中的pdf的文件路径
        col.update_one({"pdf_url": url}, {"$set": {"pdf_path": filePath}})

    def reset(self):
        '''
        所有的pdf url visit置false
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        col.update_many({}, {"$set": {"pdfVisit": False}})

    # 新的run
    def run(self, poolSize=2):
        for t in self.pdfUrls:
            if "signup" in t:
                continue
            else:
                self.pdfUrlsUseful.append(t)
        count = len(self.pdfUrlsUseful)
        print(count)
        # 构造线程参数
        args = []
        for index in range(0, count):
            pdfurlSplit = self.pdfUrlsUseful[index].split("/")
            # fileName = pdfurlSplit[len(pdfurlSplit) - 1]
            # 改动，filename用的那一串数字
            fileName = pdfurlSplit[5] + "-" + pdfurlSplit[6]
            # 这里路径或许要换成绝对路径，相对不知道为啥找不到
            args.append((None, {
                'url': self.pdfUrlsUseful[index],
                "fileName": "/Users/jamesmark/Desktop/" + fileName
            }))
        # print(args)
        # 线程池大小
        if count < poolSize:
            poolSize = count
        pool = threadpool.ThreadPool(poolSize)
        requests = threadpool.makeRequests(self.downloadFile, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()


if __name__ == '__main__':
    pdfManager = PDFManager()
    pdfManager.run()
