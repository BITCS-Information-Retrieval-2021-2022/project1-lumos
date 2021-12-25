import pymongo
import config


class SecondLevelManager:
    database = config.db
    collection = "ACMSecondLevelUrls"  # 爬取的url将要保存的表名

    def __init__(self):
        '''
                 https://www.aclweb.org/anthology/venues/anlp/ 为2级
        '''
        # self.database = database  # 爬取的url将要保存的数据库名

        # self.collection = "SecondLevelUrls"  # 爬取的url将要保存的表名
        self.client = pymongo.MongoClient(host=config.host,
                                          port=config.port,
                                          username=config.username,
                                          password=config.psw,
                                          authSource=self.database)
        # self.client = pymongo.MongoClient("mongodb://localhost:27017/")

    def hasInMongoDb(self, url):
        '''
        判断这个二级url是否已经存入数据库中
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        url_ = col.find({"url": url})
        count = 0
        for temp in url_:
            count += 1
        if count == 0:
            return False
        else:
            return True

    def saveSecondLevelUrls(self, url):
        '''
        保存二级url
        :param urls:
        :return:
        '''
        db = self.client[self.database]
        col = db[self.collection]
        col.insert_one({"url": url})

    def deleteSecondLevelUrls(self, url):
        db = self.client[self.database]
        col = db[self.collection]
        col.delete_one({"url": url})
