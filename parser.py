#!/usr/bin/python
# -*- coding: utf-8 -*-
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
import csv
import argparse
import glob
import os
from base64 import b64encode
import requests

FOCUS_TAG_DICT = {"A": "Apache Committer Insights",
                  "B": "Business Adoption",
                  "C": "Cloud and Operations",
                  "D": "Application Development",
                  "F": "Future of Apache Hadoop",
                  "G": "Governance and Security",
                  "I": "IoT and Streaming",
                  "M": "Modern Data Applications",
                  "P": "Sponsor",
                  "S": "Data Science, Analytics and Spark"
                  }

VIDEO_FILE_SUFFIX = '.mp4'

class TechTalkItem:
    _title = ''
    _speakers = []
    _video_link = ''
    _video_dl_link = ''
    _slide_link = '' 
    _slide_dl_link = '' 
    _focus_tag = ''
    _desc = ''
    def __init__(self, title='', speakers=None, video_link='', slide_link='', focus_tag='', desc=''):
        self._title = title
        self._speakers = speakers
        self._video_link = video_link
        self._slide_link = slide_link
        self._focus_tag = focus_tag
        self._desc = desc
    def display(self):
        print 'title: %s\nspeakers: %s\nvideo_link: %s\nvideo_dl_link: %s\nslide_link: %s\nslide_dl_link: %s\nfocus_tag: %s\ndescription: %s\n' % \
            (self._title,\
             self._speakers, \
             self._video_link, \
             self._video_dl_link, \
             self._slide_link, \
             self._slide_dl_link, \
             self._focus_tag, \
             self._desc)
    def toDict(self):
        dict = {"title": self._title,
                "video_link": self._video_link,
                "video_dl_link": self._video_dl_link,
                "slide_link": self._slide_link,
                "slide_dl_link": self._slide_dl_link,
                "focus_tag": self._focus_tag,
                "desc": self._desc }
        i = 0
        for speaker in self._speakers:
            dict["speaker" + i.str() + "_name"] = self._speakers[i]["name"]
            dict["speaker" + i.str() + "_corp"] = self._speakers[i]["corp"]
            dict["speaker" + i.str() + "_bio"] = self._speakers[i]["bio"]
        return dict

#class SparkSummitHtmlParser:

class HadoopSummitHtmlParser:
    def parse(self, htmlDoc):
        soup = BeautifulSoup(htmlDoc, 'html.parser')

        item_list = []
        gridViewDiv = soup.find(id="GridView")
        detailDivParent = None
        detailDiv = None
        if gridViewDiv:
            for item in gridViewDiv.find_all("div", re.compile("^lvtitleg*")):
                title = ''
                video_link = ''
                slide_link = ''
                focus_tag = ''
                desc = ''

                # get title
                it = item
                if it: title = it.string.encode('utf-8')

                # get video link 
                it = item.parent.find("span", "videolink")
                if it and it.a: video_link = it.a.get('href').encode('utf-8')

                # get slides link 
                it = item.parent.find("span", "slideslink")
                if it and it.a: slide_link = it.a.get('href').encode('utf-8')

                # get focus tag
                it = item.parent.find("div", re.compile("^keyin*"))
                if it: focus_tag = it.get_text().encode('utf-8')

                # get target div which includes: desc, speakers' biography
                descId = "%s%s" % ("desc_", item.get('id').split('_')[1])
                if not detailDivParent:
                    detailDivParent = soup.find(id=descId).parent
                detailDiv = detailDivParent.find(id=descId)

                # get description
                desc = detailDiv.p.get_text().encode('utf-8')

                # get speakers' biography
                it = detailDiv.p.next_sibling.next_sibling# <p></p>
                speakers_bio = it.get_text().encode('utf-8') # may include both speaker1 and speaker2's bio

                # get speakers' name and corp
                speakerList = []
                speakers = detailDiv.find_all("strong")
                for it in speakers:
                    speakerDict = {}
                    (name, corp) = it.get_text().split(',', 1)
                    speakerDict["name"] = name.strip().encode('utf-8')
                    speakerDict["corp"] = corp.strip().encode('utf-8')
                    speakerList.append(speakerDict)
                if len(speakerList) == 2:
                    # split speakers' bio into two
                    (bio1, bio2) = speakers_bio.split(speakerList[1]["name"] + ", " + speakerList[1]["corp"])
                    speakerList[0]["bio"] = bio1
                    speakerList[1]["bio"] = bio2
                elif len(speakerList) == 1:
                    speakerList[0]["bio"] = speakers_bio

                if title:
                    tech_talk = {}
                    tech_talk["title"] = title
                    tech_talk["desc"] = desc
                    tech_talk["speakers"] = speakerList
                    tech_talk["video_link"] = video_link
                    tech_talk["video_dl_link"] = '' 
                    tech_talk["slide_link"] = slide_link 
                    tech_talk["slide_dl_link"] = '' 
                    tech_talk["focus_tag"] = focus_tag
                    item_list.append(tech_talk)

        return item_list

class SlideSniffer:
    _URL_TEMPLATE = """http://www.slideshare.net/savedfiles?s_title=%s&user_login=HadoopSummit"""
    _MAX_RETRY_NUM = 3
    _proxies = { 'http': 'http://pico:pico2009server@127.0.0.1:8780', 
                 'https': 'http://pico:pico2009server@127.0.0.1:8780' }
    _headers = {
        'Cookie': 'bcookie="v=2&3b4b4888-5101-4f60-84ab-8e40eb6a545e"; tos_update_banner_shows=3; fbm_2490221586=base_domain=.www.slideshare.net; logged_in=381442; _uv_id=1191546341; ssdc=381442; _bizo_bzid=6b68dd39-d948-423d-aa2c-ea79d04f4e8a; _bizo_cksm=C0220F664422DAED; _cookie_id=8b7082a0272552e496fa874c788f5350; sso_redirect=true; language=en; _bizo_np_stats=; flash=---%2B%250Asig%253A%2B919b099f8ff715615d807514e5833390874d1374%250Adata%253A%2B%257C%250A%2B%2B---%2B%250A%2B%2Bused%253A%2B%2521ruby%252Fobject%253ASet%2B%250A%2B%2B%2B%2Bhash%253A%2B%257B%257D%250A%2B%2B%250A%2B%2Bvals%253A%2B%250A%2B%2B%2B%2B%253Apermanent%253A%2B%250A%2B%2B%2B%2B%253Awarning%253A%2B%250A%2B%2B%2B%2B%253Amodal_notice%253A%2B%250A%2B%2B%2B%2B%253Amessage%253A%2B%250A%2B%2B%2B%2B%253Adwnldloop%253A%2B%250A%2B%2B%2B%2B%253Anotice%253A%2B%250A%2B%2B%2B%2B%253Aunverdwnld%253A%2B%250A%2B%2B%2B%2B%253Aerror%253A%2B%250A%2B%2B%2B%2B%253Asuccess%253A%2B%250A%250A; SERVERID=r87|WHLoa|WHLeJ; linkedin_oauth_y4wa9oe4c6nu_crc=null; RT=nu=http%3A%2F%2Fwww.slideshare.net%2FHadoopSummit%2Fim-being-followed-by-drones&cl=1483949884134; __utmd=1; __utma=186399478.62612271.1474419275.1483923284.1483925619.47; __utmb=186399478.1.9.1483949886693; __utmc=186399478; __utmz=186399478.1482836804.37.16.utmcsr=dzone.com|utmccn=(referral)|utmcmd=referral|utmcct=/; __utmv=186399478.|1=member_type=FREE=1',
        'Origin': 'http://www.slideshare.net',
        'Accept-Encoding': 'gzip, deflate',
        'X-CSRF-Token': 'M25b9ujaocY8r1jhUz9MGG8aZLvxIXOfv6/tdBDkpQA=',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4,fr;q=0.2,de;q=0.2',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36',
        'Proxy-Authorization': 'Basic cGljbzpwaWNvMjAwOXNlcnZlcg==',
        'Accept': '*/*',
        'Referer': '',
        'X-Requested-With': 'XMLHttpRequest',
        'Proxy-Connection': 'keep-alive',
        'Content-Length': '0' }

    def sniff(self, list):

        i = 0
        for dict in list:
            url = self._URL_TEMPLATE % (dict['slide_link'].split('/')[-1])
            self._headers['Referer'] = dict['slide_link']
            # retry several times to fetch slide download link
            for j in range(self._MAX_RETRY_NUM):
                try:
                    response = requests.post(url, timeout=5, headers=self._headers,
                            proxies=self._proxies)
                    break
                except:
                    print "%d timeout for:  %s" % (j, dict['slide_link'])
            rep = json.loads(response.content)
            if rep['success'] == True:
                dict['slide_dl_link'] = rep['download_ss_url'].encode('ascii')
                print "%d success" % (i)
            else:
                print "Failed to fetch download link for slide:%s" % \
                    (dict['slide_link'])
                print response
            i += 1
            if i > 500:
                break
        return list


class pdfSlideDownloaderUtils():
    def __init__(self, url):
        self._url = url

    def fetchImageUrl(self):
        _site = urllib.urlopen(self._url)
        _arvore = _parse.fromstring(_site.read())
        _site.close()
        _slides = _arvore.xpath('//img[@class="slide_image"]')
        slide_cntr=1
        imgurl_list = []
        for _slide in _slides:
            print "slide: %d" % (slide_cntr)
            _s = _slide.get("data-full")
            imgurl = "%ss_%0.9d.jpg" % (_s, slide_cntr)
            imurl_list.append(imgurl)
            slide_cntr+=1
        return imgurl_list

    def convertImg2Pdf(self, srcDir, dstDir, imgNamePrefix):
        img_files = glob.glob(srcDir + "/" + imgNamePrefix + "*")
        # rename images by padding zero to it sequence number, e.g. rename "im-being-followed-by-drones-1-1024.jpg" 
        # to "im-being-followed-by-drones-001-1024.jpg"
        i = 1
        for oldname in img_files:
            newname = "%s/imgNamePrefix-%03d-1024.jpg" % (srcDir, i) 
            os.rename(oldname, newname)
            i += 1
        pdfFileName = "%s/%s.pdf" % (dstDir, imgNamePrefix)
        os.system("convert %s/%s*.jpg %s" % (srcDir, imgNamePrefix, pdfFileName))


class VideoSniffer:
    _driver = None
    _PROXY = {'host': '127.0.0.1', 'port': '8780', 'usr': 'pico', 'pwd': 'pico2009server'}
    def __init__(self):
        fp = webdriver.FirefoxProfile()
        firebug_ext = '/home/shen/.mozilla/firefox/5e9ceske.default/extensions/firebug@software.joehewitt.com.xpi'
        closeproxy_ext = '/home/shen/.mozilla/firefox/yioplo2g.testfirefoxplugin/extensions/closeproxyauth.vaka@gmail.com.xpi'
        fp.add_extension(firebug_ext)
        fp.add_extension(closeproxy_ext)

        fp.set_preference('network.proxy.type', 2)
        fp.set_preference('network.proxy.http', self._PROXY['host'])
        fp.set_preference('network.proxy.http_port', int(self._PROXY['port']))
        fp.set_preference('network.proxy.ssl', self._PROXY['host'])
        fp.set_preference('network.proxy.ssl_port', int(self._PROXY['port']))
        fp.set_preference('network.proxy.socks', self._PROXY['host'])
        fp.set_preference('network.proxy.socks_port', int(self._PROXY['port']))
        fp.set_preference('network.proxy.ftp', self._PROXY['host'])
        fp.set_preference('network.proxy.ftp_port', int(self._PROXY['port']))
        fp.set_preference('network.proxy.no_proxies_on', 'localhost, 127.0.0.1')
        credentials = '{usr}:{pwd}'.format(**self._PROXY)
        credentials = b64encode(credentials.encode('ascii')).decode('utf-8')
        fp.set_preference('extensions.closeproxyauth.authtoken', credentials)
        self._driver = webdriver.Firefox(firefox_profile=fp)
    def sniff(self, list, exclude_set):
        try:
            self._driver.get("http://en.savefrom.net")
            i = 0
            for dict in list:
                if dict["video_link"] and (dict["video_file_name"] not in exclude_set):
                    try:
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
                            # By replacing title string to change download file's name
                            title_str = "%s%s" % ("&title=", dict["video_file_name"].split(VIDEO_FILE_SUFFIX)[0])
                            dict['video_dl_link'] = re.sub(r'&title=.*$', title_str, video_dl_link)
                        i = i+1
                        if i > 20:
                            break
                    except :
                        print dict["title"]
                    finally:
                        pass
                # debug
                if dict["video_file_name"] in exclude_set:
                    msg = "exclude: %s" % (dict["video_file_name"])
                    print msg
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
        list = parser.parse(self._html_doc)
        self._item_list = sorted(list, key=lambda k: k['title'])
        self.replaceFocusTag()

    def replaceFocusTag(self):
        for item in self._item_list:
            if item["focus_tag"] in FOCUS_TAG_DICT.keys():
                item["focus_tag"] = FOCUS_TAG_DICT[item["focus_tag"]]

    def normalizeTitle(self):
        for item in self._item_list:
            title = item['title']
            title = re.sub(r'[^A-Z^a-z^0-9^\.^\'^,]',r' ', title)
            title = re.sub(' +',' ', title)
            item['title'] = title.strip()

    def genVideoFileName(self):
        for item in self._item_list:
            title = item['title']
            title = re.sub(r'[^A-Z^a-z^0-9^]',r' ', title)
            title = re.sub(' +','_', title.strip())
            item['video_file_name'] = title + VIDEO_FILE_SUFFIX

    def dumpToJson(self, file):
        with open(file, 'w') as outfile:
            json.dump(self._item_list, outfile, indent=4, sort_keys=True)

    def dumpToCsv(self, file):
        with open(file, 'w') as csvfile:
            fieldnames = ['title', 'focus_tag', 'desc', 'speaker1_name', \
                          'speaker1_corp', 'speaker1_bio', 'speaker2_name', \
                          'speaker2_corp', 'speaker2_bio', 'video_link', 'slide_link']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for item in self._item_list:
                # convert tech_talk item to a dictionary
                dict = item.copy()
                del dict["speakers"]
                i = 1
                for speaker in item["speakers"]:
                    dict["speaker" + str(i) + "_name"] = speaker["name"]
                    dict["speaker" + str(i) + "_corp"] = speaker["corp"]
                    dict["speaker" + str(i) + "_bio"] = speaker["bio"]
                    i += 1
                writer.writerow({k.encode('utf-8'):v.encode('utf-8') for k,v in dict.items()})


    def dumpVideoDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._item_list:
                dl_link = item['video_dl_link']
                if dl_link: outfile.write(dl_link + '\n')

    def dumpSlideDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._item_list:
                dl_link = item['slide_dl_link']
                if dl_link: outfile.write(dl_link + '\n')

    def dumpTitle(self, file):
        with open(file, 'w') as outfile:
            for item in self._item_list:
                title = item['title'].encode('utf-8')
                if title : outfile.write(title + '\n')

    def loadFromJson(self, file):
        with open(file, 'r') as infile:
            list = json.loads(infile.read())
            self._item_list = sorted(list, key=lambda k: k['title'])

    def download_slide(self, output_dir):

    def sniffVideoDlLink(self, sniffer, exclude_dict):
        self._item_list = sniffer.sniff(self._item_list, exclude_dict)

    def sniffSlideDlLink(self, sniffer):
        self._item_list = sniffer.sniff(self._item_list)

    def genSlideImgUrl(self, infile,):


def getVideoFileSet(dir):
    video_files = glob.glob(dir + "/*" + VIDEO_FILE_SUFFIX)
    video_files = [os.path.basename(file) for file in video_files]
    video_set = set(video_files)
    return video_set

if __name__ == "__main__":    

    arg_parser = argparse.ArgumentParser(description='Hadoop Summit Parser')
    arg_parser.add_argument('-f', '--func', dest='func', required=True, help='function options: parse, sniff_vlink, sniff_slink, dump_as_csv, dump_vlink, dump_slink, dump_title')
    arg_parser.add_argument('-i', '--input ', dest='input', required=True, help='input file or uri')
    arg_parser.add_argument('-o', '--output', dest='output', required=True, help='output file')

    args = arg_parser.parse_args()
    if not (args.func == 'parse') and \
       not (args.func == 'sniff_vlink') and \
       not (args.func == 'sniff_slink') and \
       not (args.func == 'dump_as_csv') and \
       not (args.func == 'dump_vlink') and \
       not (args.func == 'dump_slink') and \
       not (args.func == 'dump_title'):
        arg_parser.print_help()

    if args.func == 'parse':
        parser = HadoopSummitHtmlParser()
        summit = HadoopSummit(uri = args.input)
        summit.loadHtmlDoc()
        summit.parseHtmlDoc(parser)
        summit.replaceFocusTag()
        summit.normalizeTitle()
        summit.genVideoFileName()
        summit.dumpToJson(args.output)

    elif args.func == 'sniff_vlink':
        # get files that have been downloaded
        exclude_set = getVideoFileSet("/mnt/hgfs/HadoopSummit2016_sanjoe")
        sniffer = VideoSniffer()
        summit = HadoopSummit() 
        summit.loadFromJson(args.input)
        summit.sniffVideoDlLink(sniffer, exclude_set)
        summit.dumpToJson(args.output)

    elif args.func == 'sniff_slink':
        sniffer = SlideSniffer()
        summit = HadoopSummit() 
        summit.loadFromJson(args.input)
        summit.sniffSlideDlLink(sniffer)
        summit.dumpToJson(args.output)

    elif args.func == 'dump_as_csv':
        summit = HadoopSummit()
        summit.loadFromJson(args.input)
        summit.dumpToCsv(args.output)

    elif args.func == 'dump_vlink':
        summit = HadoopSummit()
        summit.loadFromJson(args.input)
        summit.dumpVideoDlLink(args.output)

    elif args.func == 'dump_slink':
        summit = HadoopSummit()
        summit.loadFromJson(args.input)
        summit.dumpSlideDlLink(args.output)

    elif args.func == 'dump_title':
        summit = HadoopSummit()
        summit.loadFromJson(args.input)
        summit.dumpTitle(args.output)

    elif args.func == 'download_slide':
        summit = HadoopSummit()
        summit.loadFromJson(args.input)

    else:
        arg_parser.print_help()
