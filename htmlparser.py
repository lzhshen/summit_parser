#!/usr/bin/python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import re
import argparse
from summit import SummitDocUtil, TechTalk
import os
import requests

class SparkSummitParser:
    _proxies = { 'http': 'http://pico:pico2009server@127.0.0.1:8780', 
                 'https': 'http://pico:pico2009server@127.0.0.1:8780' }

    def parse(self, htmlDoc):
        soup = BeautifulSoup(htmlDoc, 'html.parser')
        tt_list = []
        i = 1
        for item in soup.find_all('ul', 'summit-schedule--event--speakers list-unstyled'):
            title = ''
            desc = ''
            tag = ''
            speakers = []
            video = {'src_url': '', 'dl_link': ''}
            slide = {'src_url': '', 'dl_link': ''}

            parent = item.parent
            # title
            title = parent.h2.a.get_text().strip().encode('utf-8')
            # description
            detail_link = parent.h2.a.get('href')
            print "%d: fetching techtalk's description for %s" % (i, detail_link)
            response = requests.get(detail_link, timeout=30, proxies=self._proxies)
            desc_doc = response.content
            desc_soup = BeautifulSoup(desc_doc, 'html.parser')
            desc_p_list = desc_soup.find('div', 'event-description').find_all('p')
            if len(desc_p_list) == 2:
                desc = desc_p_list[1].get_text()
            # speakers
            for li in parent.ul.find_all("li"):
                speaker = {}
                speaker['name'] = li.a.get_text().strip().encode('utf-8')
                speaker_link = li.a.get('href')
                corp = li.span.get_text().strip().encode('utf-8')
                speaker['corp'] = re.sub(r'[()]',r'', corp)
                
                print "fetching speaker's bio for %s" % (speaker['name'])
                response = requests.get(speaker_link, timeout=30, proxies=self._proxies)
                speaker_doc = response.content
                speaker_soup = BeautifulSoup(speaker_doc, 'html.parser')
                speaker['bio'] = speaker_soup.find('div', 'speaker-bio').find('p').get_text()
                speakers.append(speaker)
            # video and slide link
            meta = parent.find_all('div', 'summit-schedule--event--metadata')[-1].find_all('a')
            if len(meta) >= 1:
                video['src_url'] = meta[0].get('href')
            if len(meta) >= 2:
                slide['src_url'] = meta[1].get('href')
            # tag
            tag_div = parent.find('div', 'summit-schedule--event--focus')
            if tag_div:
                tag = tag_div.get_text()

            # append to techtalk list 
            tt = TechTalk(title=title, speakers=speakers, desc=desc, \
                          tag=tag, video=video, slide=slide, ttt='spark')
            tt_list.append(tt)

            # test
            i += 1
            if i > 5:
                break

        return tt_list
            

class HadoopSummitParser:

    def parse(self, htmlDoc):
        soup = BeautifulSoup(htmlDoc, 'html.parser')

        tt_list = []
        gridViewDiv = soup.find(id="GridView")
        detailDivParent = None
        detailDiv = None
        if gridViewDiv:
            for item in gridViewDiv.find_all("div", re.compile("^lvtitleg*")):
                title = ''
                desc = ''
                tag = ''
                speakers = []
                video = {'src_url': '', 'dl_link': ''}
                slide = {'src_url': '', 'dl_link': ''}
                
                # get title
                it = item
                if not it.string: 
                    continue# skip crash cause
                if it: title = it.string.encode('utf-8')

                # get video link 
                it = item.parent.find("span", "videolink")
                if it and it.a: video['src_url'] = it.a.get('href').encode('utf-8')

                # get slides link 
                it = item.parent.find("span", "slideslink")
                if it and it.a: slide['src_url'] = it.a.get('href').encode('utf-8')

                # get focus tag
                it = item.parent.find("div", re.compile("^keyin*"))
                if it: tag = it.get_text().encode('utf-8')

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
                    # append to techtalk list 
                    tt = TechTalk(title=title, speakers=speakerList, desc=desc, \
                                  tag=tag, video=video, slide=slide, ttt='hadoop')
                    tt_list.append(tt)

        return tt_list


if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description='Hadoop/Spark Summit Parser')
    arg_parser.add_argument('-f', '--func', dest='func', required=True, help='function options: hadoop, spark')
    arg_parser.add_argument('-i', '--input ', dest='input', required=True, help='html file')
    arg_parser.add_argument('-o', '--output', dest='output', required=True, help='json output file')

    # validate arguments
    args = arg_parser.parse_args()
    if not (args.func == 'hadoop') and not (args.func == 'spark'):
        arg_parser.print_help()

    # choose parser 
    parser = None
    if args.func == 'hadoop':
        parser = HadoopSummitParser()
    elif args.func == 'spark':
        parser = SparkSummitParser()
    else:
        arg_parser.print_help()

    # parse html document
    util = SummitDocUtil()
    util.parseHtmlDoc(args.input, parser)
    util.dumpToJson(args.output)
