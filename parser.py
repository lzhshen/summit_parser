#!/usr/bin/python
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.proxy import *
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import sys
import simplejson as json
import time

class TechTalkItem:
    _title = ''
    _speaker = ''
    _video_link = ''
    _video_dl_link = ''
    _slide_link = '' 
    _slide_dl_link = '' 
    _focus_tag = ''
    _desc = ''
    def __init__(self, title='', speaker='', video_link='', slide_link='', focus_tag='', desc=''):
        self._title = title
        self._speaker = speaker
        self._video_link = video_link
        self._slide_link = slide_link
        self._focus_tag = focus_tag
        self._desc = desc
    def display(self):
        print 'title: %s\nspeaker: %s\nvideo_link: %s\nvideo_dl_link: %s\nslide_link: %s\nslide_dl_link: %s\nfocus_tag: %s\ndescription: %s\n' % \
            (self._title,\
             self._speaker, \
             self._video_link, \
             self._video_dl_link, \
             self._slide_link, \
             self._slide_dl_link, \
             self._focus_tag, \
             self._desc)
    def toDict(self):
        dict = {"title": self._title,
                "speaker": self._speaker,
                "video_link": self._video_link,
                "video_dl_link": self._video_dl_link,
                "slide_link": self._slide_link,
                "slide_dl_link": self._slide_dl_link,
                "focus_tag": self._focus_tag,
                "desc": self._desc }
        return dict
    def fromDict(self, dict):
        self._title = dict["title"]
        self._speaker = dict["speaker"]
        self._video_link = dict["video_link"]
        self._video_dl_link = dict["video_dl_link"]
        self._slide_link = dict["slide_link"]
        self._slide_dl_link = dict["slide_dl_link"]
        self._focus_tag = dict["focus_tag"]
        self._desc = dict["desc"]

    def getVideoLink(self):
        return self._video_link
    def setVideoDlLink(self, dl_link):
        self._video_dl_link = dl_link
    def getSlideLink(self):
        return self._slide_link
    def setSlideDlLink(self, dl_link):
        self._slide_dl_link = dl_link


class HadoopSummitHtmlParser:
    def parse(self, htmlDoc):
        soup = BeautifulSoup(htmlDoc, 'html.parser')

        i = 0
        item_list = []
        gridViewDiv = soup.find(id="GridView")
        descDivParent = None
        if gridViewDiv:
            for item in gridViewDiv.find_all("div", re.compile("^lvtitleg*")):
                title = ''
                speaker = ''
                video_link = ''
                slide_link = ''
                focus_tag = ''
                desc = ''

                # get title
                it = item
                if it: title = it.string.encode('utf-8')

                # get description
                descId = "%s%s" % ("desc_", it.get('id').split('_')[1])
                if not descDivParent:
                    descDivParent = soup.find(id=descId).parent
                desc = descDivParent.find(id=descId).p.get_text().encode('utf-8')

                # get speaker
                it = item.parent.find("div", "speaks")
                if it: speaker = it.get_text().encode('utf-8')

                # get video link 
                it = item.parent.find("span", "videolink")
                if it and it.a: video_link = it.a.get('href').encode('utf-8')

                # get slides link 
                it = item.parent.find("span", "slidelink")
                if it and it.a: slide_link = it.a.get('href').encode('utf-8')

                # get focus tag
                it = item.parent.find("div", re.compile("^keyin*"))
                if it: focus_tag = it.get_text().encode('utf-8')

                if title:
                    techTaskItem = TechTalkItem(title, speaker, video_link, slide_link, focus_tag, desc)
                    item_list.append(techTaskItem.toDict())
                    #techTaskItem.display()

                i = i+1
                if i > 10: 
                   break 

        return item_list

class Sniffer:
    _driver = None
    def __init__(self):
        self._driver = webdriver.Firefox()
    def sniffVideoDlLink(self, list):
        try:
            self._driver.get("http://en.savefrom.net")
            for dict in list:
                if dict["video_link"]:
                    # submit video url
                    inputElement = WebDriverWait(self._driver, 30).until(EC.presence_of_element_located((By.ID, "sf_url")))
                    inputElement.clear()
                    inputElement.send_keys(dict["video_link"])
                    inputElement.submit()

                    # fetch video download link
                    linkDiv = WebDriverWait(self._driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "def-btn-box")))
                    link = linkDiv.find_elements_by_xpath(".//a")
                    if link:
                        video_dl_link = link[0].get_attribute("href")
                        dict["video_dl_link"] = video_dl_link
        finally:
            self._driver.quit()
            return list 


class HadoopSummit:
    _src = 'FILE' # support 'FILE' and 'URL'
    _uri = ''  # a file path or an url
    _html_doc = ''
    _item_list = []
    def __init__(self, uri='', src='FILE'): 
        self._uri = uri
        self._src = src
        # TODO: validate both src and uri

    def loadHtmlDoc(self):
        # TODO: if _src == 'URL'
        if self._src == 'FILE':
            with open(self._uri, 'r') as f:
                self._html_doc = f.read()

    def parseHtmlDoc(self, parser):
        self._item_list = parser.parse(self._html_doc)

    def dumpToJson(self, file):
        with open(file, 'w') as outfile:
            json.dump(self._item_list, outfile, indent=4, sort_keys=True)

    def loadFromJson(self, file):
        with open(file, 'r') as infile:
            self._item_list = json.loads(infile.read())

    def display(self):
        for item in self._item_list:
            tech_talk = TechTalkItem()
            tech_talk.fromDict(item)
            tech_talk.display()

    def sniffVideoDlLink(self, sniffer):
        self._item_list = sniffer.sniffVideoDlLink(self._item_list)

if __name__ == "__main__":    
    parser = HadoopSummitHtmlParser()
    summit = HadoopSummit(uri = "/home/shen/tmp/san-joe-june.html")
    summit.loadHtmlDoc()
    summit.parseHtmlDoc(parser)
    summit.dumpToJson("/tmp/san.json")
    sniffer = Sniffer()
    summit = HadoopSummit() 
    summit.loadFromJson("/tmp/san.json")
    summit.sniffVideoDlLink(sniffer)
    summit.dumpToJson("/tmp/san_sniff.json")
