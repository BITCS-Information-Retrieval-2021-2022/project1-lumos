from apscheduler.schedulers.blocking import BlockingScheduler
from Springer.utils.SpringerUrls import SpringerUrlsCrawler
from Springer.utils.SpringerContent import SpringerContent
from Springer.utils.PDFDownloader import PDFManager
from tqdm import tqdm
# import time
import datetime


def run_spider():
    print("启动爬虫")
    starttime = datetime.datetime.now()

    url1 = 'https://link.springer.com/search?facet-content-type="ConferenceProceedings"'
    url2 = 'https://link.springer.com/search?facet-content-type="Journal"'
    springerCrawler = SpringerUrlsCrawler()
    springerCrawler.getConferencefromTopLevel(url1)
    springerCrawler.getJournalfromTopLevel(url2)

    springerContent = SpringerContent()
    urls1 = springerContent.getUnvisitUrls(
        springerContent.collectionConferenceUrl)
    urls2 = springerContent.getUnvisitUrls(
        springerContent.collectionJournalUrl)
    print(len(urls1), len(urls2))
    # log("Crawling from conference:\n")
    pbar = tqdm(urls1)
    for url_ in pbar:
        pbar.set_description("Crawling %s" % url_)
        paperInfo = springerContent.getContentfromConferencePaper(url_)
        if not paperInfo:
            continue
        springerContent.savePaperInfoToMongoDb(paperInfo)
        springerContent.updateUrls(url_,
                                   springerContent.collectionConferenceUrl)
        # log("Paper *** " + url_ + " *** download.\n")
    # log("\n")
    # log("Crawling from journal:\n")
    pbar = tqdm(urls2)
    for url_ in pbar:
        pbar.set_description("Crawling %s" % url_)
        paperInfo = springerContent.getContentfromJournalPaper(url_)
        print(paperInfo)
        if not paperInfo:
            continue
        springerContent.savePaperInfoToMongoDb(paperInfo)
        springerContent.updateUrls(url_, springerContent.collectionJournalUrl)
        # log("Paper *** " + url_ + " *** download.\n")

    pdfManager = PDFManager()
    pdfManager.run()

    endtime = datetime.datetime.now()
    print("爬虫运行结束，用时为：")
    print(endtime - starttime)


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(run_spider, 'cron', hour=24, minute=0)
    sched.start()
