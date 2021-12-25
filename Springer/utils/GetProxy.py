
from requests.models import Response
from lxml import etree
import requests
import random
import time
import re


class WebRequest(object):
    name = "web_request"

    def __init__(self, *args, **kwargs):
        self.response = Response()

    @property
    def user_agent(self):
        """
        return an User-Agent at random
        :return:
        """
        ua_list = [
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)',
            'Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0',
        ]
        return random.choice(ua_list)

    @property
    def header(self):
        """
        basic header
        :return:
        """
        return {'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Connection': 'keep-alive',
                'Accept-Language': 'zh-CN,zh;q=0.8'}

    def get(self, url, header=None, retry_time=3, retry_interval=5, timeout=5, *args, **kwargs):
        """
        get method
        :param url: target url
        :param header: headers
        :param retry_time: retry time
        :param retry_interval: retry interval
        :param timeout: network timeout
        :return:
        """
        headers = self.header
        if header and isinstance(header, dict):
            headers.update(header)
        while True:
            try:
                self.response = requests.get(url, headers=headers, timeout=timeout, *args, **kwargs)
                return self
            # except Exception as e:
                retry_time -= 1
                if retry_time <= 0:
                    resp = Response()
                    resp.status_code = 200
                    return self
                time.sleep(retry_interval)

    @property
    def tree(self):
        return etree.HTML(self.response.content)

    @property
    def text(self):
        return self.response.text

    @property
    def json(self):
        try:
            return self.response.json()
        except Exception as e:
            return {}


'''
这个函数作用是：从5个提供代理ip的网站爬取代理ip，并随即返回1个ip，以此来实现ip池的功能，处理反爬虫的问题
'''


def getProxy(key):
    if key == 1:
        # print("key1:")
        urls = ['https://ip.ihuan.me/address/5Lit5Zu9.html']
        proxies_list = []
        for url in urls:
            r = WebRequest().get(url, timeout=10)
            proxies = re.findall(r'>\s*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*?</a></td><td>(\d+)</td>', r.text)
            for proxy in proxies:
                p = {"http": proxy[0] + ":" + proxy[1]}
                proxies_list.append(p)
        # rint(proxies_list)
        if len(proxies_list) == 0:
            return None
        return proxies_list[random.randint(0, len(proxies_list) - 1)]
    elif key == 2:
        # print("key2:")
        urls = ['http://www.ip3366.net/free/?stype=1', "http://www.ip3366.net/free/?stype=2"]
        proxies_list = []
        for url in urls:
            r = WebRequest().get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                p = {"http": proxy[0] + ":" + proxy[1]}
                proxies_list.append(p)
        # print(proxies_list)
        if len(proxies_list) == 0:
            return None
        return proxies_list[random.randint(0, len(proxies_list) - 1)]
    elif key == 3:
        # print("key3:")
        r = WebRequest().get("https://www.89ip.cn/index_1.html", timeout=10)
        proxies_list = []
        proxies = re.findall(r'<td.*?>[\s\S]*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\s\S]*?</td>'
                             r'[\s\S]*?<td.*?>[\s\S]*?(\d+)[\s\S]*?</td>', r.text)
        for proxy in proxies:
            p = {"http": proxy[0] + ":" + proxy[1]}
            proxies_list.append(p)
        # print(proxies_list)
        if len(proxies_list) == 0:
            return None
        return proxies_list[random.randint(0, len(proxies_list) - 1)]
    elif key == 4:
        # print("key4:")
        url = "https://www.dieniao.com/FreeProxy.html"
        tree = WebRequest().get(url, verify=False).tree
        proxies_list = []
        for li in tree.xpath("//div[@class='free-main col-lg-12 col-md-12 col-sm-12 col-xs-12']/ul/li")[1:]:
            ip = "".join(li.xpath('./span[1]/text()')).strip()
            port = "".join(li.xpath('./span[2]/text()')).strip()
            p = {"http": str(ip) + ":" + str(port)}
            proxies_list.append(p)
        # print(proxies_list)
        if len(proxies_list) == 0:
            return None
        return proxies_list[random.randint(0, len(proxies_list) - 1)]
    elif key == 5:
        # print("key5:")
        target_urls = ["http://www.kxdaili.com/dailiip.html", "http://www.kxdaili.com/dailiip/2/1.html"]
        proxies_list = []
        for url in target_urls:
            tree = WebRequest().get(url).tree
            for tr in tree.xpath("//table[@class='active']//tr")[1:]:
                ip = "".join(tr.xpath('./td[1]/text()')).strip()
                port = "".join(tr.xpath('./td[2]/text()')).strip()
                p = {"http": str(ip) + ":" + str(port)}
                proxies_list.append(p)
        # print(proxies_list)
        if len(proxies_list) == 0:
            return None
        return proxies_list[random.randint(0, len(proxies_list) - 1)]


if __name__ == "__main__":
    for i in range(1, 6):
        getProxy(i)
