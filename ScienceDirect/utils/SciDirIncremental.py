from apscheduler.schedulers.blocking import BlockingScheduler
from ScienceDirect.utils.SciDirUrlsCrawler import SciDirUrlsCrawler
from ScienceDirect.utils.ContentManager import ContentManager
from ScienceDirect.utils.PDFDownloader import PDFManager
import datetime


def run_spider():
    print("启动爬虫")
    starttime = datetime.datetime.now()

    SciDirCrawler = SciDirUrlsCrawler()
    SciDirCrawler.getSciDirUrls()

    contentManager = ContentManager()
    Urls = contentManager.getUnvisitedUrls()
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

    pdfManager = PDFManager()
    pdfManager.run()

    endtime = datetime.datetime.now()
    print("爬虫运行结束，用时为：")
    print(endtime - starttime)


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(run_spider, 'cron', hour=24, minute=0)
    sched.start()
