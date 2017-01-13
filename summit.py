#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import simplejson as json
import csv
import os
import pprint
from json import JSONEncoder

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

class TechTalk:

    def __init__(self, title='', desc='', tag='', video=None, slide=None, speakers=None, ttt='hadoop'):
        self._type = ttt 
        self._data = {
            'title': '',
            'desc': '',
            'tag': '',
            'video': {'src_url': '', 'dl_link': '', 'fname': ''},
            'slide': {'src_url': '', 'dl_link': '', 'fname': ''},
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
    
    def genVideoFileName(self):
        title = self._data['title']
        title = re.sub(r'[^A-Z^a-z^0-9^]',r' ', title)
        title = re.sub(' +','_', title.strip())
        self._data['video']['fname'] = title + VIDEO_FILE_SUFFIX

    def getVideoDlLink(self):
        return self._data['video']['dl_link']

    def getSlideDlLink(self):
        return self._data['slide']['dl_link']

    def getTitle(self):
        return self._data['title']

class SummitDocUtil:
    _item_list = []

    def parseHtmlDoc(self, fname, parser):
        doc = None
        with open(fname, 'r') as f:
            doc = f.read()
        ll = parser.parse(doc)
        self._item_list = sorted(ll, key=lambda k: k['title'])
        self.extendTag()
        self.stripTitle()
        self.genVideoFileName()

    def extendTag(self):
        for item in self._item_list:
            item.extendTag()

    def stripTitle(self):
        for item in self._item_list:
            item.stripTitle()

    def genVideoFileName(self):
        for item in self._item_list:
            item.genVideoFileName()

    def loadFromJson(self, file):
        with open(file, 'r') as infile:
            l = json.loads(infile.read())
            l = sorted(l, key=lambda k: k['title'])
        for item in l:
            tt = TechTalk()
            tt._data = item
            self._item_list.append(tt)


    def dumpToJson(self, file):
        with open(file, 'w') as outfile:
            tt_list = [item._data for item in self._item_list]
            json.dump(tt_list, outfile, indent=4, sort_keys=True)

    def dumpToCsv(self, file):
        with open(file, 'w') as csvfile:
            fieldnames = ['title', 'tag', 'desc', 'speaker1_name', \
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
                dl_link = item.getVideoDlLink()
                if dl_link: outfile.write(dl_link + '\n')

    def dumpSlideDlLink(self, file):
        with open(file, 'w') as outfile:
            for item in self._item_list:
                dl_link = item.getSlideDlLink()
                if dl_link: outfile.write(dl_link + '\n')

    def dumpTitle(self, file):
        with open(file, 'w') as outfile:
            for item in self._item_list:
                title = item.getTitle()
                if title : outfile.write(title + '\n')


if __name__ == "__main__":    
    pass
