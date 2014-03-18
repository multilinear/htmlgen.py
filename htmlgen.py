#!/usr/bin/python2.7

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
import HTMLParser
import os
import re
import sys
import StringIO
import time
from bs4 import BeautifulSoup

src_base = 'dummy'
dest_base = 'dummy'
curdir = 'dummy'

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
  dest_base = os.path.join(os.getcwd(), rel_dest_dir)
  # This will be overridden at each file layer to be the current files dir
  curdir = '.'
  print '*** Initializing htmlgen ***'
  print 'curdir:', curdir
  print 'src_base:', src_base
  print 'dest_base:', dest_base


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
  print 'Cleaning', abspath, nodelete_abspath
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


def set_perms(file):
  """ Sets the permissions for a file, so it's readable for serving etc.
 
  file -- The the file to set permissions on
  Returns: None
  """
  try:
    os.chown(file, os.getuid(), web_group)
    if os.path.isdir(file):
      os.chmod(file, 0o775)
    else:
      os.chmod(file, 0o664)
  except:
    pass


def create_dest(curdir):
  """ Create a destination directory to match a dir in the source tree.
  globals used:
    src_base: The source tree basepath
    dest_base: The destination tree basepath

  curdir -- The directory in the source tree that we want created
    in the destination tree.
  Return: New destination directory
  """
  dest_path = os.path.join(dest_base,
      os.path.relpath(curdir, src_base))
  try:
    os.makedirs(dest_path)
  except:
    pass
  return dest_path


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
  f = open(os.path.join(dest_path), mode='w')
  f.write(data)


def symlink_files(src_path, dest_path):
  """ symlink files in dest_path to src_path.

  src_path -- the path of the source directory to symlink to
  dest_path -- the path of the destination path to place symlinks in
  Returns: None
  """
  # Create the directory if it doesn't exist
  src_path = os.path.normpath(src_path)
  dest_path = os.path.normpath(dest_path)
  try:
    os.makedirs(dest_path)
    set_perms(dest_path)
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
    os.symlink(os.path.join(src_path, f), os.path.join(dest_path, f))
    set_perms(os.path.join(src_path, f))
    set_perms(os.path.join(dest_path, f))

# This function can be used as the only line in a file
# to index that directory and all below it
def simple_index(gen_header, gen_footer, src_dirpath=None):
  """ Build an index of a directory tree.
  globals used:
    curdir: directory to index (overriden by src_dirpath)
    src_base: base of the source hieararchy.
    dest_base: base of the destination hieararchy.
  
  gen_header -- function outputing anything that should be added to the header
    of the file. (takes title and path)
  gen_footer -- function outputing anything that should be added to the footer
    of the file. (takes title and path)
  src_dirpath -- directory to build the tree in.
  Returns: None 
  """
  global curdir
  global src_base
  global dest_base
  if src_dirpath is None:
    src_dirpath = curdir
  src_dirpath = os.path.join(src_base, src_dirpath)
  print 'simple_index', src_dirpath
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
    data += [gen_header(title, rel_path)]
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
    print 'dumping to', os.path.join(dest_path, 'index.html')
    dump_file(os.path.join(dest_path, 'index.html'), '\n'.join(data))


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
    output = StringIO.StringIO()
    old_stdout = sys.stdout
    sys.stdout = output 
    exec text in new_context
    sys.stdout = old_stdout
    return output.getvalue()

  # Note: We could do this by escaping all the HTML and sticking
  # "print" in front of it, this works great in languages that aren't python
  # in python we don't use "}" for blocks, so we can't have loops across those
  # statements anyway - therefore there's no gain, and I wrote this first.
  class MyHTMLParser(HTMLParser.HTMLParser):

    def __init__(self, context, document):
      HTMLParser.HTMLParser.__init__(self)
      self._in_pytag = False
      self._code = ''
      self._result = ''
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
          print 'ERROR:', self._document, 'Position:', self.getpos(), 'TAG:', tag
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
  soup = BeautifulSoup(parser.get_result())
  return soup.prettify()


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
    data = run_python_html(f.read(), context, src_f_path)
    dump_file(os.path.join(dest_path, f_name[:-5]+'.html'), data)


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
  execfile(srcfile, new_context)

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
