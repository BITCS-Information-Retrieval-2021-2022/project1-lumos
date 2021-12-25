# import time
import random
import pymongo
import requests
from tqdm import tqdm
# from ContentDownloader import ContentManager
# import LevelUrls as lu
import config


class VideoManager():
    '''
    爬取论文视频
    '''
    database = config.db
    collection = "ACMBasicInfo"

    def __init__(self):
        # self.database = "ACLAnthology"
        # self.collection = "Video"
        # self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        # self.ACLAnthology = "ACLAnthology"
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)
        self.VideoUrl = self.getVideoUrlsfromDB()
        random.shuffle(self.VideoUrl)

    def getVideoUrlsfromDB(self):
        '''
        从数据库中获取需要爬取视频的url
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        urls = [url['video_download'] for url in col.find({"videoVisit": False})]
        # print(urls)

        videoUrls = []
        for x in urls:
            for url in x:
                videoUrls.append(url)

        return videoUrls

    def updateUrl(self, url, filePath):
        '''
            已经爬过的pdf更新数据库的visit标记
        :param url:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        col.update_one({"video_download": url}, {"$set": {"videoVisit": True}})
        col.update_one({"video_download": url}, {"$set": {"video_path": filePath}})

    def reset(self):
        '''
        所有的video url visit置false
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        col.update_many({}, {"$set": {"videoVisit": False}})

    def downloadVideo(self, url):
        url_ = "https://dl.acm.org" + url
        print(url_)
        # url_ = "https://dl.acm.org/action/" + "downloadSupplement?doi=10.1145%2F3053332&file=1938-imwut-2017_vol1issue1.mp4"

        headers = {
            "User-Agent":
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.109 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }
        r = requests.get(url=url_, headers=headers)
        str_r = str(r)
        print(str_r)
        videoName = url[8:]
        path = "/Users/jamesmark/Desktop/video/" + videoName
        if str_r == "<Response [200]>":
            lenth = len(r.content)
            print("r.content lenth: " + str(lenth))
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            self.updateUrl(url, path)
            print("successful download video : " + url_)

    def run(self):
        pbar = tqdm(self.VideoUrl)

        for videoUrl in pbar:
            pbar.set_description("Crawling %s" % videoUrl)
            print()
            self.downloadVideo(videoUrl)

        print("videos downloading done")


if __name__ == '__main__':
    videoManager = VideoManager()
    videoManager.run()
    # print(videoManager.VideoUrl)
