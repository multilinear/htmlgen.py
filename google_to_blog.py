#!/usr/bin/python2.7

import xml.dom.minidom
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as bs

def print_thing(object):
  print xml.dom.minidom.parseString(ET.tostring(date_object)).toprettyxml()

fname = 'blog-11-25-2018.xml'
tree = ET.parse(sys.stdin)
root = tree.getroot()
for e in root.iter('{http://www.w3.org/2005/Atom}entry'):
  kind_object = e.find('{http://www.w3.org/2005/Atom}category[@term=\'http://schemas.google.com/blogger/2008/kind#post\']')
  if (kind_object is None):
    continue
  date_object = e.find('{http://www.w3.org/2005/Atom}published')
  if (date_object is None):
    continue
  content_object = e.find('{http://www.w3.org/2005/Atom}content[@type=\'html\']')
  if (content_object is None):
    continue
  title_object = e.find('{http://www.w3.org/2005/Atom}title')
  if (title_object is None or title_object.text is None):
    continue
  date = date_object.text
  title = title_object.text
  print 'found post', title, 'published', date 
  f = open(date + '_' + title + '.blog', 'w')
  soup = bs(content_object.text, from_encoding='utf8', features='lxml')
  soup.html.unwrap()
  soup.body.unwrap()
  f.write(soup.prettify('utf8'))
