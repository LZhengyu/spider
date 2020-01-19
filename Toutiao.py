import json
import os
import re
from hashlib import md5
from json import JSONDecodeError
from urllib.parse import urlencode
from multiprocessing import Pool
import pymongo
import requests
from bs4 import BeautifulSoup
from requests import RequestException
from config import *

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

def get_page_index(offset,keyword):
    data = {
        'aid': 24,
        'app_name': 'web_search',
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'en_qc': 1,
        'cur_tab': 1,
        'from': 'search_tab',
        'pd': 'synthesis',
        'timestamp': '1579142929180'
    }
    url = 'https://www.toutiao.com/api/search/content/?'+urlencode(data)
    try:
        response = requests.get(url,headers=headers,cookies=cookies)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求页面出错')
        return None

def parse_page_index(html):
    try:
        data = json.loads(html)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        pass

def get_page_detail(url):
    try:
        response = requests.get(url,headers=headers,cookies=cookies)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页面出错',url)
        return None

def parse_page_detail(html,url):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    images_pattern = re.compile('gallery: JSON.parse\("(.*?)"\),',re.S)
    result = re.search(images_pattern,html)
    if result:
        ret = result.group(1)
        ret = ret.replace("\\","")
        ret = ret.replace("u002F","/")
        data = json.loads(ret)
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return {
                'title':title,
                'url':url,
                'images':images
            }

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False

def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url,headers=headers,cookies=cookies)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片出错',url)
        return None

def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset,'街拍')
    for url in parse_page_index(html):
        # print(url)
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html,url)
            if result:
                # save_to_mongo(result)
                print(result)

if __name__ == '__main__':
    # 返回的json数据为空：原因是requests的请求对象没有加请求头和cookies
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"}
    cookies = {
        "Cookie": "tt_webid=6719272225969096196; WEATHER_CITY=%E5%8C%97%E4%BA%AC; tt_webid=6719272225969096196; csrftoken=b28e41c77cd4f268af393de7d3e9d47a; UM_distinctid=16c4159a9ae7e3-04be696c185f6c-3f385c06-1fa400-16c4159a9afa94; CNZZDATA1259612802=1303724616-1564459685-https%253A%252F%252Fwww.toutiao.com%252F%7C1564459685; WIN_WH=1536_710; s_v_web_id=e588fb5c6570d79a16b67e84decce3d8; __tasessionId=y99fyeyyt1568882979794"}
    main(0)
    # groups = [x*20 for x in range(GROUP_START,GROUP_END+1)]
    # main(groups)
    # pool = Pool()
    # pool.map(main,groups)