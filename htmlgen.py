#!/usr/bin/python3
"""
This library is designed for lightweight generation of website content.

The idea is simple. We put a make.py in each subdirectory of the hierarchy
we want in the final version. *.data files are basically html, except they
can include <python> </python> tags the content of which will be run as
python code, and the tags replaced with that codes output.

How it works:
This file should be imported into a file named "make.py" at the root
of your file hierarchies.

Variables for your use:
- src_base: this is the root of the source hierarchy
- dest_base: should never be changed, this is the root of the destination
    hierarchy
- curdir: the directory (relative to src_base) of the file being run

Particularly interesting functions:
- run_make_subdirs() can be used to run "make.py" in each subdirectory.
each subsequent layer of make.py will gain the context of the make.py
that called it. Normally used in a make.py.

- pages_from_datafiles() can be used to interpret all *.data files in that
directory. These files are basically html, but can include tags of the form
"<python> python_code </python>". The python_code will be run (all code in
the file should be run in the same context). The file will be written out to
the destination hierarchy as a .html file with the python tag replaced with
the output of it's code to standard out. Normally used in a make.py.

Dependencies:
 - beautifulsoup (debian: python-bs4)
     this is just for prettification, removing is trivial
 - httplib2 (debian: python-httplib2)
"""

import errno
from datetime import datetime
from dateutil import parser
from html.parser import HTMLParser
import os
import re
import sys
from io import StringIO
import time
from bs4 import BeautifulSoup
from xml.etree import ElementTree
import math

src_base = 'dummy'
dest_base = 'dummy'
curdir = 'dummy'
web_group = 'www-data'

def init(argv, rel_dest_dir='../website'):
  """ Call before using other functions in this library.
  
  rel_dest_dir -- is the destination directory relative to the binary being run.
  Returns: None
  """
  global src_base 
  global dest_base
  global curdir
  # In case it was run from some other path
  # it's important we work relative to the binaries location
  os.chdir(os.path.dirname(argv[0]))
  # This will be used by subsequent files to figure out the hierarchy
  # they are in.
  src_base = os.getcwd()
  # Assume we're writing to the directory below this one
  dest_base = os.path.normpath(os.path.join(os.getcwd(), rel_dest_dir))
  # This will be overridden at each file layer to be the current files dir
  curdir = '.'
  print('*** Initializing htmlgen ***')
  print('curdir:', curdir)
  print('src_base:', src_base)
  print('dest_base:', dest_base)


### Some utility functions 
def panic(msg):
  """ Just what you think, call for fatal errors. """
  print(msg)
  sys.exit(1)


def listdir(directory, exclude_patterns=None):
  """ A simple wrapper that skips special files. """
  ld = os.listdir(directory)
  if exclude_patterns:
    # go through each pattern, and drop everythign that matches it
    for p in exclude_patterns:
      ld = [d for d in ld if not re.match(p, d)]
  # put the directories back on
  return ('/'.join([directory,f]) for f in ld if f[0] != '.')


def clean(abspath=None, nodelete_abspath=None):
  """ Deletes a directory hierarchy.
  globals used:
    src_base: default for nodelete_abspath
    dest_base: default for abspath

  abspath -- The path of the directory under which everything will be deleted.
  nodelete_abspath -- a path that may be below "path" which should not be
      deleted
  Returns: None 
  """
  if abspath is None:
    abspath = dest_base
  if nodelete_abspath is None:
    nodelete_abspath = src_base
  print('Cleaning', abspath, nodelete_abspath)
  for tuple in os.walk(abspath, topdown=False):  
    (path, subdirs, files) = tuple
    # if our source directory is a prefix, we're looking at a source file
    # don't delete it!
    if nodelete_abspath:
      common = os.path.commonprefix([path, nodelete_abspath])
      if common == nodelete_abspath:
        continue
    for f in files:
      os.unlink(os.path.join(path, f))
    for s in subdirs:
      # This is just for the special case of the "src" directory
      common = os.path.commonprefix([os.path.join(path, s), nodelete_abspath])
      if nodelete_abspath and common == nodelete_abspath:
        continue
      os.rmdir(os.path.join(path, s))

def add_perms(file):
  """ Sets the permissions for a file, so it's readable for serving etc.
 
  file -- The the file to set permissions on
  Returns: None
  """
  def my_chmod(file, perm):
    os.chmod(file, os.stat(file).st_mode | perm)

  if os.path.isdir(file):
    my_chmod(file, 0o777)
  else:
    my_chmod(file, 0o664)

def dest_from_src(srcdir) :
  return os.path.join(dest_base, os.path.relpath(srcdir, src_base))

def create_dest(srcdir):
  """ Create a destination directory to match a dir in the source tree.
  globals used:
    src_base: The source tree basepath
    dest_base: The destination tree basepath

  curdir -- The directory in the source tree that we want created
    in the destination tree.
  Return: New destination directory
  """
  try:
    os.makedirs(dest_from_src(srcdir))
  except:
    pass
  return dest_from_src(srcdir)

def computeurl(cur_path_from_base, rel_link_path):
  """ Build a local link.

  Example:
    cur_path_from_base = /home/mbrewer/website/stuff
    rel_link_path = other_stuff/foo.html
    returns a link to /home/mbrewer/other_stuff/foo

  cur_path_from_base -- path we are at relative to the base of the hierarchy.
  rel_link_path -- path relative to that base.
  Return: a link to rel_link_path for use in a <a> tag
  """
  filename = []
  if cur_path_from_base != '.':
    filename = ['..' for t in cur_path_from_base.split('/')]
  filename.append(rel_link_path)
  return '/'.join(filename)

def dump_file(dest_path, data):
  """ Output a file.
  dest_path -- destination to write to.
  data -- a list of strings to be output (newlines between each string).
  Returns: None
  """
  # And dump the content to the suggested file
  print('dumping file', dest_path)
  f = open(dest_path, 'w', encoding='utf-8')
  f.write(data)

def symlink_files(src_path, dest_path):
  """ symlink files in dest_path to src_path.

  src_path -- the path of the source directory to symlink to
  dest_path -- the path of the destination path to place symlinks in
  Returns: None
  """
  #print('symlink files', src_path, dest_path)
  # Create the directory if it doesn't exist
  src_path = os.path.normpath(src_path)
  dest_path = os.path.normpath(dest_path)
  try:
    os.makedirs(dest_path)
    add_perms(dest_path)
  except:
    pass
  files = listdir(src_path)
  # Create symlinks to all the files
  for f_src_path in files:
    f = os.path.basename(f_src_path)   
    # skip build and .data files
    if f == 'make.py':
      continue
    if f[-5:] == '.data':
      continue
    if os.path.isdir(f_src_path):
      continue
    # copy would work too, this is easier in python for some reason
    # It's kindof nice for large files anyway
    #print('symlinking: ', os.path.join(src_path, f), os.path.join(dest_path, f))
    os.symlink(os.path.join(src_path, f), os.path.join(dest_path, f))
    add_perms(os.path.join(src_path, f))
    add_perms(os.path.join(dest_path, f))

def run_python_html(code, context, document_name):
  """ Run <python> tags and compile the result into an HTML string.

  code -- HTML string with <python> tags (or not). 
  context -- context to run it in
  document_name -- name of the document (for debugging purposes)
  Returns: an HTML string.
  """

  def run_python_tag(text, context):
    # fix tabbing
    lines = text.split('\n')
    # strip all spaces from the first line
    if lines[0]:
      num_spaces = 0
      while lines[0][num_spaces] == ' ':
        num_spaces += 1
      lines[0] = lines[0][num_spaces:]
    # strip the same number as line 2 from the rest
    if len(lines) > 1:
      if lines[1]:
        num_spaces = 0
        while lines[1][num_spaces] == ' ':
          num_spaces += 1
        first_line = lines[0]
        lines = [t[num_spaces:] for t in lines]
        lines[0] = first_line
    text = '\n'.join(lines)
    # run the code we have
    new_context = context.copy()
    output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = output 
    exec(text, new_context)
    sys.stdout = old_stdout
    return output.getvalue()

  # Note: We could do this by escaping all the HTML and sticking
  # "print" in front of it, this works great in languages that aren't python
  # in python we don't use "}" for blocks, so we can't have loops across those
  # statements anyway - therefore there's no gain, and I wrote this first.
  class MyHTMLParser(HTMLParser):

    def __init__(self, context, document):
      HTMLParser.__init__(self)
      self._in_pytag = False
      self._code = ''
      self._result = u''
      self._context = context
      self._document = document

    def handle_starttag(self, tag, attrs):
        if tag == 'python':
          self._in_pytag = True
          return
        try:
          attr_string = ' '.join(l + '="' + v + '"' for (l,v) in attrs)
          string = '<' + tag + ' ' + attr_string + '>'
        except:
          print('ERROR:', self._document, 'Position:', self.getpos(), 'TAG:', tag)
          string = ''
        if self._in_pytag:
          self._code += string
        else:
          self._result += string
          
    def handle_endtag(self, tag):
        if tag == 'python':
          self._in_pytag = False
          self._result += run_python_tag(self._code, self._context)
          self._code = ''
          return
        if self._in_pytag:
          self._code += '</' + tag + '>'
          return
        self._result += '</' + tag + '>'

    def handle_data(self, data):
        if self._in_pytag:
          self._code += data
          return
        self._result += data

    def get_result(self):
      return self._result
  parser = MyHTMLParser(context, document_name)
  parser.feed(code) 
  soup = BeautifulSoup(parser.get_result(), "lxml", from_encoding='utf8')
  soup.html.unwrap()
  soup.body.unwrap()
  return soup.prettify()

### Basic website building stuff
def pages_from_datafiles(context, directory=None):
  """ find .data files interpret them and output .html to destination.

  find <python> </python> tags in the HTML and pull out the code.
  Run the code and capture the output from stdout
  output the original HTML code with python tags replaced by their output.

  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  directory -- directory to search for files in
  context -- context to *copy* to then run these in
  Returns: None
  """
  global curdir
  if directory is None:
    directory = curdir 
  if directory == '':
    directory = '.'
  directory = os.path.relpath(directory, src_base)
  src_path = os.path.join(src_base, directory)
  dest_path = os.path.join(dest_base, directory)
  symlink_files(src_path, dest_path)
  l = listdir(src_path)
  for src_f_path in l:
    if os.path.isdir(src_f_path):
      continue
    f_name = os.path.basename(src_f_path)
    if f_name[-5:] != '.data':
      continue
    f = open(src_f_path)
    try:
      os.makedirs(dest_path)
    except:
      pass
    print('processing file:', f_name)
    data = run_python_html(f.read(), context, src_f_path)
    dump_file(os.path.join(dest_path, f_name[:-5]+'.html'), data)

def simple_index(gen_header, gen_footer, gen_title, src_dirpath=None):
  """ Build an index of a directory tree. Can be used as the only line
  in a file to index that directory and all below it.
  globals used:
    curdir: directory to index (overriden by src_dirpath)
    src_base: base of the source hieararchy.
    dest_base: base of the destination hieararchy.
  
  gen_header -- function outputing anything that should be added to the header
    of the file. (takes title and path)
  gen_footer -- function outputing anything that should be added to the footer
    of the file. (takes title and path)
  gen_title -- function for formatting the title, (take title and date, date may be empty)
  src_dirpath -- directory to build the tree in.
  Returns: None 
  """
  global curdir
  global src_base
  global dest_base
  if src_dirpath is None:
    src_dirpath = curdir
  src_dirpath = os.path.join(src_base, src_dirpath)
  print('simple_index', src_dirpath)
  rel_path = os.path.relpath(src_dirpath, src_base)
  dest_dirpath = os.path.join(dest_base, rel_path)
  os.makedirs(dest_dirpath)
  # Walk subdirectories
  # symlink the files
  # create the directories
  # and build index.html files for each dir
  for tup in os.walk(src_dirpath, topdown=True):
    (src_path, subdirs, files) = tup
    # Create the directory 
    rel_path = os.path.relpath(src_path, src_base)
    dest_path = os.path.join(dest_base, rel_path)
    # title is just the directory name
    title = src_path.split('/')[-1]
    # Index the directories and files
    symlink_files(src_path, dest_path)
    subdirs.sort()
    files.sort()
    entries = subdirs + files
    # get the urls for those files
    entries = [computeurl('.', f) for f in entries if f != 'make.py']
    # and output it
    data = []
    data += [gen_header(title, rel_path), gen_title(title,'')]
    data += ['<ul>']
    for entry in entries:
      data += ['<li> <a href=' + entry + '>']
      if entry in subdirs:
        data += ['<strong>' + entry + '</strong>']
      else:
         data += [entry]
      data += ['</a> </li>'] 
    data += ['</ul>']
    data += [gen_footer(title, rel_path)]
    dump_file(os.path.join(dest_path, 'index.html'), '\n'.join(data))


# Blog generation stuff
def bloglist_from_files(directory=None):
  """ find .blog files interpret them, returns a list of dictionaries
  With metadata about each file. Does NOT read content, for content see
  bloglist_dump_blog, bloglist_dump_posts and bloglist_dump_rss.

  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  directory -- directory to search for files in
  Returns: a list of dictionaries containing metadata about each blogpost
  """
  global curdir
  global src_base
  if directory is None:
    directory = curdir 
  if directory == '':
    directory = '.'
  directory = os.path.relpath(directory, src_base)
  src_path = os.path.join(src_base, directory)
  dest_path = os.path.join(dest_base, directory)
  rel_path = os.path.relpath(src_path, src_base)
  title = src_path.split('/')[-1]
  l = listdir(src_path)
  # first pass, generate the post list
  post_list=[]
  for src_f_path in l:
    if os.path.isdir(src_f_path):
      continue
    f_name = os.path.basename(src_f_path)
    if f_name[-5:] != '.blog':
      continue
    post_list.append({
        'path': src_f_path,
        'file': f_name,
        'title': f_name[:-5].split('_')[1],
        'date': f_name[:-5].split('_')[0],
        'link': f_name[:-5]+'.html'
    })
  # sort the pages by date first
  post_list.sort(key=lambda e: e['date'], reverse=True)
  return post_list

def bloglist_ammend_data(blog_list, context):
  """ using blog_list (as output by bloglist_from_files) read the contents
  of all of the files and dump it in to the 'data' field of each entry
  in the bloglist. .blog files are interpreted much like datafiles, see
  pages_from_datafiles().
  Note that on very large blogs this loads the *entire* of the blog in to
  memory.
  
  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  blog_list -- list of dicts as returned by bloglist_from_pages
  context -- context to *copy* to then run the <python> tags in
  Returns: None
  """
  for (i,e) in enumerate(blog_list):
    f = open(e['path'], 'r')
    us = f.read()
    e['data'] = run_python_html(us, context, e['path'])

def bloglist_dump_rss(site_link, blog_title, desc, post_list, gen_title, directory=None):
  """ Using blog_list (as output by bloglist_from_files and ammend by bloglist_ammend_data)
  this generates an rss.xml file for your RSS feed. You can then link this file in your
  header and users will be able to use RSS readers to follow your blog. Note that this
  publishes ALL your content in the feed, not just a link.

  Note that you may want pass the first slice of the blog_list. Usually an rss feed
  only includes the last several posts, not the entire blog for all history.

  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  site_link -- URL of your blog
  blog_title -- the title of your blog
  desc -- a description of your blog
  gen_title -- A function taking a post's title and outputting an HTML string prepended to the post
  directory -- In case you want to write it to a weird place. Defaults to local
  """
  global curdir
  global src_base
  if directory is None:
    directory = curdir 
  if directory == '':
    directory = '.'
  directory = os.path.relpath(directory, src_base)
  src_path = os.path.join(src_base, directory)
  dest_path = create_dest(src_path)
  rel_path = os.path.relpath(src_path, src_base)
  try:
    os.makedirs(dest_path)
  except:
    pass
  rss = ElementTree.Element('rss')
  rss.set('version','2.0')
  channel = ElementTree.SubElement(rss, 'channel')
  title = ElementTree.SubElement(channel, 'title')
  title.text = blog_title
  link = ElementTree.SubElement(channel, 'link')
  link.text = site_link
  description = ElementTree.SubElement(channel, 'description')
  description.text = desc
  for e in post_list:
    item = ElementTree.SubElement(channel, 'item') 
    title = ElementTree.SubElement(item, 'title')
    title.text = e['title']
    link = ElementTree.SubElement(item, 'link')
    link.text = e['link']
    pubDate = ElementTree.SubElement(item, 'pubDate')
    dt = parser.parse(e['date'])
    pubDate.text = dt.strftime('%a, %d %b %Y %H:%M:%S %z')
    enclosure = ElementTree.SubElement(item, 'enclosure')
    enclosure.text = e['data']
  fname = os.path.join(dest_path, 'rss.xml')
  dump_file(fname, ElementTree.tostring(rss, encoding='utf-8', method='xml').decode())

def bloglist_dump_posts(gen_header, gen_footer, gen_title, blog_list, directory=None):
  """ Dumps pages for each individual post in your blog. This allows for post-specific links.
  uses information stored in blog_list, as generated by bloglist_from_files() and bloglist_ammend_data()
  Content is processed like data_from_pages(), with the results of gen_header, gen_title and gen_footer
  attached

  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  gen_header -- takes a title and a path to the page (used for relative links)
  gen_footer -- takes a title and a path to the page (used for relative links)
  gen_title -- takes a title a date and an optional link
  blog_list -- as generated by bloglist_from_files() and ammended by bloglist_ammend_data()
  directory -- directory to process, defaults to local
  Returns: None
  """
  if directory is None:
    directory = curdir 
  if directory == '':
    directory = '.'
  directory = os.path.relpath(directory, src_base)
  src_path = os.path.join(src_base, directory)
  create_dest(src_path)
  dest_path = dest_from_src(src_path)
  rel_path = os.path.relpath(src_path, src_base)
  for (i,e) in enumerate(blog_list):
    file_data = [gen_header(e['title'], rel_path)]
    file_data.append(gen_title(e['title'],e['date'],e['link']))
    file_data.append(e['data'])
    file_data.append(gen_footer(e['title'], rel_path))
    dump_file(os.path.join(dest_path, e['link']), '\n'.join(file_data))

def bloglist_dump_blog(gen_header, gen_footer, gen_title, blog_list):
  """ Dumps the main blog pages
  Using the data from blog_list this concatonates all the posts together
  with pagination every so often.  The first (most recent) page will be named 
  index.html, and the rest indexI.html where I is the index of that page.

  This basically generates a half-reasonable blog format. Though it is not unlikely
  that you'll want to rewrite some component of it as it makes actual design decisions
  for you. It's been included as the author found himself copying this code between
  projects.

  uses globals:
    curdir: current directory
    src_base: base of the source hierarchy
    dest_base: base of the destination hierarchy

  gen_header -- takes a title and a path to the page (used for relative links)
  gen_footer -- takes a title and a path to the page (used for relative links)
  gen_title -- takes a title a date and an optional link
  blog_list -- as generated by bloglist_from_files() and ammended by bloglist_ammend_data()
  returns: None
  """
  print('Now Generating Blog')
  # Now generate the blog

  def gen_nav_links(count, pages, jump):
    nav='<div id=blog_nav>'
    # prev
    if (count == 0):
      nav += '<div class=left_nav> newer posts </div>'
    if (count == 1):
      nav += '<a class=left_nav href=index.html> newer posts </a>'
    elif (count != 0):
      nav += '<a class=left_nav href=index'+str(count-1)+'.html> newer posts </a>'
    # next
    if (count+1 < pages):
      nav += '<a class=right_nav href=index'+str(count+1)+'.html> older posts </a>'
    else:  
      nav += '<div class=right_nav> older posts </div>'
    nav += '</div>'
    return nav

  # this is mostly pagination logic
  fname = 'index.html'
  count = 0
  jump = 5
  i = 0
  pages = math.ceil(len(blog_list) / float(jump))
  for i in range(0, len(blog_list), jump):
    fname = os.path.join(dest_from_src(curdir), fname)
    main_blog = [gen_header('blog', curdir)]
    main_blog.append(gen_nav_links(count, pages, jump))
    hr = ''
    for e in blog_list[i:i+jump]:
      main_blog.append(hr)
      main_blog.append(gen_title(e['title'], parser.parse(e['date']).date().isoformat(), e['link']))
      main_blog.append(e['data'])
      hr = '<hr>'
    main_blog.append(gen_nav_links(count, pages, jump))
    main_blog.append(gen_footer('blog', curdir))
    dump_file(fname ,'\n'.join(main_blog))
    count += 1
    fname='index'+str(count)+'.html'

# Recursive stuff
def run_python_file(context, srcfile):
  """ Run a python file.

  Note - this depends on global variables! 
    curdir
    src_base 
    dest_base

  context -- context in which the file will be run
  srcfile -- source file to run.
  Returns: None
  """
  if srcfile[-3:] != '.py':
    panic('attempted to run a non sourcefile') 
  print('running: ' + srcfile)
  # make a new namespace, so subdirs don't pollute supers
  new_context = context.copy()
  # give it the new directory path
  new_context['htmlgen'].curdir = os.path.relpath(os.path.dirname(srcfile), src_base)
  exec(open(srcfile).read(), new_context)

def run_make_subdirs(context, directory=None, exclude_patterns=None):
  """ Runs python make.py in all subdirectories.
    
  directory -- directory to look in for subdirectories with makefiles.
  Returns: None
  """
  global curdir
  if directory is None:
    directory = curdir
  ld = listdir(directory, exclude_patterns=exclude_patterns)
  for subdir in ld:
    if not os.path.isdir(subdir):
      continue
    run_python_file(context, os.path.join(subdir, 'make.py'))
  curdir = directory
  print('Done Running run_make_subdirs() in', directory)

