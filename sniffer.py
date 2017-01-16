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
from lxml import html as _parse
from summit import SummitDocUtil, TechTalk



class PptSlideSniffer:
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

    def sniff(self, tt_list, exclude_set):

        i = 0
        for tt in tt_list:
            slink = tt.getSlideLink()
            sfname = tt.getPptSlideFineName()
            if slink and (sfname not in exclude_set):
                url = self._URL_TEMPLATE % (slink.split('/')[-1])
                self._headers['Referer'] = slink
                # retry several times to fetch slide download link
                for j in range(self._MAX_RETRY_NUM):
                    try:
                        response = requests.post(url, timeout=5, headers=self._headers,
                                proxies=self._proxies)
                        break
                    except:
                        print "%d timeout for:  %s" % (j, slink)
                rep = json.loads(response.content)
                if rep['success'] == True:
                    s_dl_link = rep['download_ss_url'].encode('ascii')
                    tt.setPptSlideDlLink(s_dl_link)
                    print "%d success" % (i)
                else:
                    print "Failed to fetch download link for slide:%s" % \
                        (slink)
                    print response
            i += 1
            if i > 500:
                break
        return list


class pdfSlideDownloaderUtils():

    @staticmethod
    def fetchImageUrlInfo(self, url):
        site = urllib.urlopen(url)
        arvore = _parse.fromstring(site.read())
        site.close()
        slides = arvore.xpath('//img[@class="slide_image"]')
        page_num = len(slides)
        imgurl_tmpl = ''
        if page_num > 0:
            s = _slide.get("data-full")
            imgurl_tmpl = _s + 's_%0.9d.jpg'
        return (imgurl_tmpl, page_num)

    @staticmethod
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

class PdfSlideSniffer:
    def sniff(self, tt_list, exclude_set):
        i = 0
        for tt in tt_list:
            slink = tt.getSlideLink()
            sfname = tt.getPdfSlideFileName()
            if slink and (sfname not in exclude_set):
                (imgurl_tmpl, page_num) = pdfSlideDownloaderUtils.fetchImageUrlInfo(slink)
                tt.setPdfSlideImgInfo(imgurl_tmpl, page_num)
        return tt_list

class VideoSniffer:
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
    def sniff(self, tt_list, exclude_set):
        try:
            print "tt_list size: %d" % (len(tt_list))
            self._driver.get("http://en.savefrom.net")
            i = 0
            for tt in tt_list:
                vlink = tt.getVideoLink()
                vfname = tt.getVideoFileName()
                if vlink and (vfname not in exclude_set):
                    try:
                        # submit video url
                        inputElement = WebDriverWait(self._driver, 30).until(EC.presence_of_element_located((By.ID, "sf_url")))
                        inputElement.clear()
                        inputElement.send_keys(vlink)
                        inputElement.submit()

                        # fetch video download link
                        linkDiv = WebDriverWait(self._driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "def-btn-box")))
                        link = linkDiv.find_elements_by_xpath(".//a")
                        if link:
                            v_dl_link = link[0].get_attribute("href")
                            # By replacing title string to change download file's name
                            title_str = "%s%s" % ("&title=", vfname.split(VIDEO_FILE_SUFFIX)[0])
                            v_dl_link_new = re.sub(r'&title=.*$', title_str, v_dl_link)
                            tt.setVideoDlLink(v_dl_link_new)
                        i = i+1
                        if i > 20:
                            break
                    except :
                        print tt.getTitle()
                    finally:
                        pass
                # debug
                if vfname in exclude_set:
                    msg = "exclude: %s" % (vfname)
                    print msg
        finally:
            self._driver.quit()
            return tt_list 


def getExcludeSet(dir, suffix):
    files = glob.glob(dir + "/*" + suffix)
    files = [os.path.basename(file) for file in files]
    exclude_set = set(files)
    return exclude_set 

if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description='Hadoop/Spark Video/Slide Sniffer')
    arg_parser.add_argument('-f', '--func', dest='func', required=True, help='function options: sniff_vlink, sniff_ppt_slink, sniff_pdf_slink')
    arg_parser.add_argument('-i', '--input ', dest='input', required=True, help='input json file')
    arg_parser.add_argument('-o', '--output', dest='output', required=True, help='output file')
    arg_parser.add_argument('-d', '--dir', dest='dir', required=True, help='Video/Slide download directory')

    args = arg_parser.parse_args()
    if not (args.func == 'sniff_vlink') and \
       not (args.func == 'sniff_ppt_slink') and \
       not (args.func == 'sniff_pdf_slink'):
        arg_parser.print_help()

    # load json file
    util = SummitDocUtil()
    util.loadFromJson(args.input)

    # choose sniffer and start to sniff download link for video or slide
    sniffer = None
    if args.func == 'sniff_vlink':
        exclude_set = getExcludeSet(args.dir, '.mp4')
        sniffer = VideoSniffer()
        util.sniff(sniffer, exclude_set)
        util.dumpVideoDlLink(args.output)
    elif args.func == 'sniff_pdf_slink':
        exclude_set = getExcludeSet(args.dir, '.pdf')
        sniffer = PdfSlideSniffer()
        util.sniff(sniffer, exclude_set)
        util.dumpPdfSlideImgDlLink(args.output)
    elif args.func == 'sniff_ppt_slink':
        exclude_set = getExcludeSet(args.dir, '.pptx')
        sniffer = PptSlideSniffer()
        util.sniff(sniffer, exclude_set)
        util.dumpPptSlideDlLink(args.output)
    else:
        arg_parser.print_help()
