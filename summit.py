#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import simplejson as json
import csv
import os
import pprint
from json import JSONEncoder
import copy
import argparse

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

class TechTalk:
    VIDEO_FILE_SUFFIX = '.mp4'
    SLIDE_FILE_SUFFIX_PDF = '.pdf'
    SLIDE_FILE_SUFFIX_PPT = '.pptx'

    def __init__(self, title='', desc='', tag='', video=None, slide=None, speakers=None, ttt='hadoop'):
        self._type = ttt 
        self._data = {
            'title': '',
            'desc': '',
            'tag': '',
            'base_fname': '',
            'video': {'src_link': '', 'dl_link': ''},
            'slide': {'src_link': '', 'dl_link': '', 'imgurl_tmpl': '', 'page_num': 0},
            'speakers': []
        }
        self._data['title'] = title
        self._data['desc'] = desc
        self._data['tag'] = tag
        if video: self._data['video'] = video
        if slide: self._data['slide'] = slide
        if speakers: self._data['speakers'] = speakers
    
    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __str__(self):
        pp = pprint.PrettyPrinter(indent=4)
        return str(pp.pprint(self._data))

    def extendTag(self):
        if self._type == 'hadoop':
            if self._data["tag"] in FOCUS_TAG_DICT.keys():
                self._data["tag"] = FOCUS_TAG_DICT[self._data["tag"]]
    
    def stripTitle(self):
        title = self._data['title']
        title = re.sub(r'[^A-Z^a-z^0-9^\.^\'^,]',r' ', title)
        title = re.sub(' +',' ', title)
        self._data['title'] = title.strip()
    
    def genBaseFileName(self):
        fname = self._data['title']
        fname = re.sub(r'[^A-Z^a-z^0-9^]',r' ', fname)
        fname = re.sub(' +','_', fname.strip())
        self._data['base_fname'] = fname

    def setPdfSlideImgInfo(self, imgurl_tmpl, page_num):
        self._data['slide']['imgurl_tmpl'] = imgurl_tmpl
        self._data['slide']['page_num'] = page_num

    def getPdfSlideImgInfo(self):
        imgurl_tmpl = self._data['slide']['imgurl_tmpl']
        page_num = self._data['slide']['page_num']
        return (imgurl_tmpl, page_num)

    ## get/set ##

    def getTitle(self):
        return self._data['title']

    def getSlideLink(self):
        return self._data['slide']['src_link']

    def setPptSlideDlLink(self, link):
        self._data['slide']['dl_link'] = link

    def getVideoLink(self):
        return self._data['video']['src_link']

    def getVideoFileName(self):
        return self._data['base_fname'] + '.mp4'

    def getPptSlideFileName(self):
        return self._data['base_fname'] + '.pptx'

    def getPdfSlideFileName(self):
        return self._data['base_fname'] + '.pdf'

    def getVideoDlLink(self):
        return self._data['video']['dl_link'] if self._data['video']  else ''

    def setVideoDlLink(self, link):
        print "set video link for %s" % (self._data['title'])
        self._data['video']['dl_link'] = link

    def getSlideDlLink(self):
        return self._data['slide']['dl_link']

    def setSlideDlLink(self, link):
        return self._data['slide']['dl_link']


    @staticmethod
    def getFieldNameForCsv():
        fieldnames = ['title', 'tag', 'desc', 'speaker1_name', \
                      'speaker1_corp', 'speaker1_bio', 'speaker2_name', \
                      'speaker2_corp', 'speaker2_bio']
        return fieldnames

    def getFieldValueForCsv(self):
        item = copy.deepcopy(self._data)
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(item)
        del item['speakers']
        del item['video']
        del item['slide']
        i = 1
        for speaker in self._data['speakers']:
            item['speaker' + str(i) + '_name'] = speaker['name']
            item['speaker' + str(i) + '_corp'] = speaker['corp']
            item['speaker' + str(i) + '_bio'] = speaker['bio']
            i += 1
        return item

class SummitDocUtil:
    _tt_list = []

    def parseHtmlDoc(self, fname, parser):
        doc = None
        with open(fname, 'r') as f:
            doc = f.read()
        ll = parser.parse(doc)
        self._tt_list = sorted(ll, key=lambda k: k['title'])
        self.extendTag()
        self.stripTitle()
        self.genBaseFileName()

    def extendTag(self):
        for item in self._tt_list:
            item.extendTag()

    def stripTitle(self):
        for item in self._tt_list:
            item.stripTitle()

    def genBaseFileName(self):
        for item in self._tt_list:
            item.genBaseFileName()

    def loadFromJson(self, file):
        with open(file, 'r') as infile:
            l = json.loads(infile.read())
            l = sorted(l, key=lambda k: k['title'])
        for item in l:
            tt = TechTalk()
            tt._data = item
            self._tt_list.append(tt)


    def dumpToJson(self, file):
        with open(file, 'w') as outfile:
            tt_list = [item._data for item in self._tt_list]
            json.dump(tt_list, outfile, indent=4, sort_keys=True)

    def dumpToCsv(self, file):
        with open(file, 'w') as csvfile:
            fieldnames = TechTalk.getFieldNameForCsv()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for item in self._tt_list:
                # convert tech_talk item to a dictionary
                d = item.getFieldValueForCsv()
                writer.writerow({k.encode('utf-8'):v.encode('utf-8') for k,v in d.items()})

    def dumpVideoDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._tt_list:
                dl_link = item.getVideoDlLink()
                if dl_link: outfile.write(dl_link + '\n')

    def dumpPptSlideDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._tt_list:
                dl_link = item.getSlideDlLink()
                if dl_link: outfile.write(dl_link + '\n')

    def dumpPdfSlideImgDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._tt_list:
                (imgurl_tmpl, page_num) = item in getPdfSlideImgInfo()
                for i in range(1, page_num):
                    imgurl = imgurl_tmpl % (page_num)
                    outfile.write(imgurl + '\n')

    def dumpTitle(self, file):
        with open(file, 'w') as outfile:
            for item in self._tt_list:
                title = item.getTitle()
                if title : outfile.write(title + '\n')
    
    def sniff(self, sniffer, exclude_set):
        self._tt_list = sniffer.sniff(self._tt_list, exclude_set)

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='Hadoop/Spark Summit Utility')
    arg_parser.add_argument('-f', '--func', dest='func', required=True, help='function options: to_csv, dump_vlink, dump_ppt_slink, dump_img_slink')
    arg_parser.add_argument('-i', '--input ', dest='input', required=True, help='input json file')
    arg_parser.add_argument('-o', '--output', dest='output', required=True, help='output file')

    # validate arguments
    args = arg_parser.parse_args()
    if not (args.func == 'to_csv') and \
       not (args.func == 'dump_vlink') and \
       not (args.func == 'dump_ppt_slink') and \
       not (args.func == 'dump_img_slink'):
        arg_parser.print_help()

    util = SummitDocUtil()
    util.loadFromJson(args.input)
    if args.func == 'to_csv':
        util.dumpToCsv(args.output)
    elif args.func == 'dump_vlink':
        util.dumpVideoDlLink(args.output)
    elif args.func == 'dump_ppt_slink':
        util.dumpPptSlideDlLink(args.output)
    elif args.func == 'dump_img_slink':
        util.dumpPdfSlideImageDlLink(args.output)
    else:
        arg_parser.print_help()

