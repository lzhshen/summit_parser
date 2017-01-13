#!/usr/bin/python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import re
import argparse
from summit import SummitDocUtil, TechTalk

class SparkSummitParser:

    def parse(self, htmlDoc):
        soup = BeautifulSoup(htmlDoc, 'html.parser')
        tt_list = []

        for item in soup.find_all('ul', 'summit-schedule--event--speakers list-unstyled'):
            title = ''
            desc = ''
            tag = ''
            speakers = []
            video = {'src_url': '', 'dl_link': '', 'fname': ''}
            slide = {'src_url': '', 'dl_link': '', 'fname': ''}

            parent = item.parent
            #title
            title = parent.h2.a.get_text().encode('utf-8')
            detail_link = parent.h2.a.get('href')
            # speakers
            for li in parent.ul.find_all("li"):
                speaker = {}
                speaker['name'] = li.a.get_text().strip().encode('utf-8')
                speaker['detail_link'] = li.a.get('href')
                corp = li.span.get_text().strip().encode('utf-8')
                speaker['corp'] = re.sub(r'[()]',r'', corp)
                speakers.append(speaker)
            # video and slide link
            meta = parent.find_all('div', 'summit-schedule--event--metadata')[-1].find_all('a')
            if len(meta) >= 1: 
                video['src_url'] = meta[0].get('href')
            if len(meta) >= 2:
                slide['src_url'] = meta[1].get('href')

            # append to techtalk list 
            tt = TechTalk(title=title, speakers=speakers, desc=desc, \
                          tag=tag, video=video, slide=slide)
            tt_list.append(tt)

        return tt_list
            

class HadoopSummitParser:

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
                if not it.string: 
                    continue# skip crash cause
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
