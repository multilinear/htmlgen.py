#!/usr/bin/python3

import os
from bs4 import BeautifulSoup as bs

current = os.getcwd()
ld = os.listdir()

# Get all of the IDs used in blog posts
imgs = []
iframes = []
for name in ld:
  if os.path.basename(name)[-5:] == '.blog':
    f = open(name, 'r')
    soup = bs(f.read(), 'lxml')
    imgs += soup.find_all('img')
    imgs_src = [i['src'] for i in imgs]
    iframes += soup.find_all('iframe')
    iframes_src = [i['src'] for i in iframes]

ids = []
for i in imgs_src:
  if 'flickr' not in i: 
    continue
  p_id = i.split('/')[-1].split('_')[0]
  ids.append(p_id)

for i in iframes_src:
  if 'flickr' not in i: 
    continue
  p_id = i.split('/')[5] 
  ids.append(p_id)

used_ids = ids

# Get all of the IDs existing on flickr
f = open('all_photo_ids')
all_ids = f.readlines()
all_ids = [i.strip() for i in all_ids]

for i in all_ids 
  print(i)


