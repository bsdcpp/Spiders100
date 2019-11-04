# -*- coding:utf-8 -*-
# Author: https://github.com/Hopetree
# Date: 2019/8/10

'''
新浪微盘资源下载，不需要模拟浏览器，完全使用接口调用
'''

import os, sys
import re
import time
import json
from concurrent.futures import ThreadPoolExecutor
import requests
from lxml import etree


class Weipan(object):
    def __init__(self, url, output):
        self.baseurl = url
        self.items = []
        self.output = output
        self.sub_baseurl = ''

    def get_item_list(self, url, ctype):
        res = requests.get(url).text
        tree = etree.HTML(res)

        # 提取当前页所有资源，存入列表
        item_selectors = tree.xpath('//div[@class="sort_name_intro"]/div/a')
        ftype = tree.xpath('//div[@class="sort_name_pic"]/a/@class')
        for item_selector, ft in zip(item_selectors, ftype):
            link = item_selector.get('href')
            title = item_selector.get('title')
            if ft == 'vd_icon32_v2 vd_folder':
                self.sub_baseurl = link
                self.get_item_list(link, 'folder')
            else:
                self.items.append((link, title))


        # 提取下一页链接，进行递归爬取
        next_page_selectors = tree.xpath('//div[@class="vd_page"]/a[@class="vd_bt_v2 vd_page_btn"]')
        for next_page_selector in next_page_selectors:
            next_text = next_page_selector.xpath('./span')[0].text.strip()
            if next_text == "下一页":
                if ctype == 'folder':
                    next_url = self.sub_baseurl + next_page_selector.get('href')
                    self.get_item_list(next_url, 'folder')
                else:
                    next_url = self.baseurl + next_page_selector.get('href')
                    self.get_item_list(next_url, 'link')

    def get_callback_info_by_item(self, item):
        '''
        提取一个资源页面的有效信息，用来构造请求url
        '''
        url, title = item
        res = requests.get(url).text
        id = re.findall("CURRENT_URL = 'vdisk.weibo.com/s/(.*?)'", res)[0]
        sign = re.findall("SIGN = '(.*?)'", res)[0]
        url_temp = 'https://vdisk.weibo.com/api/weipan/fileopsStatCount?link={id}&ops=download&wpSign={sign}&_={timestr}'
        timestr = int(time.time() * 1000)
        callback = url_temp.format(id=id, sign=sign, timestr=timestr)
        return url, callback

    def get_load_info_by_callback_info(self, callback_info):
        '''
        请求回调地址，返回资源下载地址等信息
        '''
        url, callback = callback_info
        headers = {
            'Referer': url,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
        }
        res = requests.get(callback, headers=headers).text
        data = json.loads(res)
        name = data.get('name')
        path = data.get('path')
        load_url = data.get('url')
        print(url, callback, path, load_url)
        return path, load_url

    def load(self, load_info):
        path, load_url = load_info
        content = requests.get(load_url).content
        savename = os.path.join(self.output, path)
        os.makedirs(os.path.dirname(savename), 0o755, True)
        with open(savename, 'wb+') as f:
            f.write(content)
        print('{} load done'.format(path))

    def load_by_item(self, item):
        '''
        线程执行的函数
        '''
        callback_info = self.get_callback_info_by_item(item)
        load_info = self.get_load_info_by_callback_info(callback_info)
        self.load(load_info)

    def main(self):
        # 收集资源下载信息
        self.get_item_list(self.baseurl, 'link')
        # 多线程下载资源
        with ThreadPoolExecutor(max_workers=8) as pool:
            pool.map(self.load_by_item, self.items)


if __name__ == '__main__':
    URL = 'http://vdisk.weibo.com/s/uGmF42vqqKUnm'
    URL = sys.argv[1]
    OUTPUT = r'liang2'
    wp = Weipan(URL, OUTPUT)
    wp.main()
