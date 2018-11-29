htmlgen.py
==========

Highly flexible html generation library for python - designed for very lightweight development of static content. Also has features for blogging such as RSS feed generation and permalinks.

I was annoyed at how heavyweight everything I could find was, so sometime ago I wrote some crappy python scripts to help manage my own website, to ensure common headers and footers and that sort of thing. I continued development on it for a couple of years until it was not so crappy. After glancing around for other options it seems there are tons for ruby and none for python. So, I decided to clean it up and publish it.

Deps:
There are a couple of dependencies, see htmlgen.py for what to install - it's not much I promise.

Concept:
The idea is simple. It's a directory hierarchy just like you want in your final website. In each directory there's a make.py file. This allows for arbitrary complexity as desired by the user. make.py files inherit context from the make.py file in the parent directory, allowing you to build up a library of useful functions for a portion of your site.

Next there's some supplied functions for taking a ".data" file, which is in essence a .html file, but can contain <python> and </python> tags. The functions will take a .data file and convert it to a .html file. Whatever is between the <python> tags gets interpeted and it's output replaces the tags in the resulting .html file.

Your root "make.py" file should look something like this:

import htmlgen

htmlgen.init(sys.argv)
htmlgen.clean()
htmlgen.pages_from_datafiles(globals())
htmlgen.run_make_subdirs(globals())

The other make.py files should generally look like this, but only the last two lines. Of course, you may want to do something much more interesting in your make.py files occasionally (I do). for example using the simple_index() function. This is just the default setup that will interpret .data files through your hierarchy.

I use this library by writing "def gen_header(title, path)" in my top make.py. Then I place <python> generate_header(title, date) </python> at the begining of each path and similar for the footer at the end. This way I always get consistant pages, and only have to write that code once. If you look at the blog generation code this use-case becomes more obvious.

For more details on exact use etc. see htmlgen.py docstrings

This library also contains 2 other scripts:
- google_to_blog.py is a script I used to convert the XML files I downloaded from google in to my blog when moving off blogger. It's not flawless (for example, it finds drafts, not just published content), but you may find it useful.
- new_blog_post.sh is a trivial shell script that, given a blog title will generate the file containing it using the current time as the time as the "posted" time. I use this to start a new blog post.

Known Flaws:
Path handling is a disaster. It's grown organically as I've expanded the
library, and it needs a major overhaul. I appolagize for the complex uses of
htmlgen.computeurl required *everywhere*, it's the cause of a lot of bugs in
final websites.
