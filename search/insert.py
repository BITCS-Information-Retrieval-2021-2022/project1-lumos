from elasticsearch import Elasticsearch
import json

import pymongo

db = "paper"
host = "10.108.18.24"
port = 27017
es_path = "localhost"
es_port = "9200"

f = open("config_retrieval")
for line in f.readlines():

    component = line.strip().split(" = ")
    if component[0] == "host":
        host = component[1]
    elif component[0] == "db":
        db = component[1]
    elif component[0] == "port":
        port = component[1]
    elif component[0] == "es_path":
        es_path = component[1]
    elif component[0] == "es_port":
        es_port = component[1]

myclient = pymongo.MongoClient('mongodb://' + host + ':' + port + '/')

mydb = myclient[db]


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def toelastic(db, es):
    cnt = 0
    for x in db.find({}, {"_id": 0, "video_download": 0, "pdf_download": 0, "pdfVisit": 0, "videoVisit": 0}):
        cnt += 1
        st = x['year']
        author = x['authors']
        if (not isinstance(author, list)):
            authors = [x.strip() for x in author.split(",")]
            x['authors'] = authors
        if (st != '' and is_number(st) and int(st) < 10):
            print(x['year'])
        elif (st != '' and is_number(st)):
            es.index(index="paper", body=x)


if __name__ == '__main__':

    es = Elasticsearch(es_path + ':' + es_port)

    template = open('index_template.json', encoding='utf-8')

    mappings = json.load(template)

    if es.indices.exists(index='paper') is not True:
        res = es.indices.create(index='paper', body=mappings)
    else:
        es.indices.delete(index='paper')
        res = es.indices.create(index='paper', body=mappings)
    mydb.list_collections()
    collist = mydb.list_collection_names()
    for sites in collist:  # 判断 sites 集合是否存在
        print("集合" + sites + "已存在！")
        if "BasicInfo" in sites:
            toelastic(mydb[sites], es)
