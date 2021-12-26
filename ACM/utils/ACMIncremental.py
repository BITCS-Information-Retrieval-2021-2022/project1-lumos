from apscheduler.schedulers.blocking import BlockingScheduler
from ACM.utils.ACMUrlsCrawler import ACMUrlsCrawler
from ACM.utils.ContentDownloader import ContentManager
from ACM.utils.PDFDownloader import PDFManager
from ACM.utils.VideoDownloader import VideoManager
from tqdm import tqdm
import time
import datetime


def run_spider():
    print("启动爬虫")
    starttime = datetime.datetime.now()

    acmUrlsCrawler = ACMUrlsCrawler()
    acmUrlsCrawler.saveUrlToMongoDb()

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

    pdfManager = PDFManager()
    pdfManager.run()

    videoManager = VideoManager()
    videoManager.run()

    endtime = datetime.datetime.now()
    print("爬虫运行结束，用时为：")
    print(endtime - starttime)


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(run_spider, 'cron', hour=24, minute=0)
    sched.start()
