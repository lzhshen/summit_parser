#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import argparse
import glob
import os
from lxml import html as _parse
import simplejson as json
import urllib


class PdfSlideDownloaderUtils():

    def fetchImageUrl(self, slide_url):
        _site = urllib.urlopen(slide_url)
        _arvore = _parse.fromstring(_site.read())
        _site.close()
        _slides = _arvore.xpath('//img[@class="slide_image"]')
        slide_cntr=1
        imgurl_list = []
        for _slide in _slides:
            #print "slide: %d" % (slide_cntr)
            _s = _slide.get("data-full")
            imgurl = "%ss_%0.9d.jpg" % (_s, slide_cntr)
            imgurl_list.append(imgurl)
            slide_cntr+=1
        return imgurl_list

    def getImageFilePrefix(self, imgurl):
       return imgurl.split('-1-1024.jpg') [0].split('/')[-1]

    def convertImg2Pdf(self, indir, outdir, img_prefix):
        img_files = glob.glob(indir + "/" + img_prefix + "*")
        # rename images by padding zero to it sequence number, e.g. rename "im-being-followed-by-drones-1-1024.jpg" 
        # to "im-being-followed-by-drones-001-1024.jpg"
        for oldname in img_files:
            idx = oldname.split('-1024.jpg')[0].split('-')[-1]
            newname = "%s/%s-%0.4d.jpg" % (indir, img_prefix, int(idx)) 
            print "%s ==> %s" % (oldname, newname)
            os.rename(oldname, newname)
        filename = "%s/%s.pdf" % (outdir, img_prefix)
        os.system("convert %s/%s-*.jpg %s" % (indir, img_prefix, filename))

def loadFromJson(file):
    sort_list = []
    with open(file, 'r') as infile:
        list = json.loads(infile.read())
        sort_list = sorted(list, key=lambda k: k['title'])
    return sort_list

def dumpToJson(sort_list, file):
    with open(file, 'w') as outfile:
        json.dump(sort_list, outfile, indent=4, sort_keys=True)

def genImgUrl(jsonfile, urlfile):
    slist = loadFromJson(jsonfile)
    util = PdfSlideDownloaderUtils()
    for item in slist:
        print "start fetching image links for %s" % (item['slide_link'])
        imgurls = util.fetchImageUrl(item['slide_link'])
        print "fetch completed! Totaly %d images" % (len(imgurls))
        with open(urlfile, 'a+') as outfile:
            for url in imgurls:
                outfile.write(url + "\n") 
        # get Image prefix
        prefix = util.getImageFilePrefix(imgurls[0])
        item['slide_image_prefix'] = prefix
    # dump to json which include "slide_image_prefix"
    new_jsonfile = "%s%s.json" % (jsonfile.split(".json")[0], "_with_image_prefix")
    dumpToJson(slist, new_jsonfile)

def genPdf(jsonfile, indir, outdir):
    slist = loadFromJson(jsonfile)
    util = PdfSlideDownloaderUtils()
    for item in slist:
        util.convertImg2Pdf(indir, outdir, item['slide_image_prefix'])

if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description='slide downloader')
    arg_parser.add_argument('-f', '--func', dest='func', required=True, help='function options: genImgUrl, genPdf')
    arg_parser.add_argument('-j', '--json', dest='jsonfile', required=True, help='json file')
    arg_parser.add_argument('-i', '--input ', dest='input', required=False, help='input directory or file')
    arg_parser.add_argument('-o', '--output', dest='output', required=True, help='output directory file')

    args = arg_parser.parse_args()
    if not (args.func == 'genImgUrl') and \
       not (args.func == 'genPdf'):
        arg_parser.print_help()

    if args.func == 'genImgUrl':
        genImgUrl(args.jsonfile, args.output)

    elif args.func == 'genPdf':
        genPdf(args.jsonfile, args.input, args.output)

    else:
        arg_parser.print_help()
