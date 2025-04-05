# MIGRATED!
This repo is abandoned in protest of Microsoft and US politics, please see https://codeberg.org/multilinear/htmlgen.py

htmlgen.py
==========

## What is it
Highly flexible html generation library for python - designed for very lightweight development of static content. Also has features for blogging such as RSS feed generation and permalinks.

I was annoyed at how heavyweight everything I could find was, so sometime ago I wrote some crappy python scripts to help manage my own website, to ensure common headers and footers and that sort of thing. I continued development on it for a couple of years until it was not so crappy. After glancing around for other options it seems there are tons for ruby and none for python. So, I decided to clean it up and publish it.

## Concept:
The idea is simple. It's a directory hierarchy just like you want in your final website. In each directory there's a make.py file. This allows for arbitrary complexity as desired by the user. make.py files inherit context from the make.py file in the parent directory, allowing you to build up a library of useful functions for a portion of your site.

Next there's some supplied functions for taking a ".data" file, which is in essence a .html file, but can contain <python> and </python> tags. The functions will take a .data file and convert it to a .html file. Whatever is between the <python> tags gets interpeted and it's output replaces the tags in the resulting .html file.

In general this library tries to make as few design choices as possible with respect to websites it generates. Most of it can be used to generate virtually any site. There is nothing stopping you from outputting javascript and other dynamic stuff as well.

## Deps:
There are a couple of dependencies, see htmlgen.py for what to install - it's not much I promise.

## Usage
Your root "make.py" file should look something like this:
```
#!/usr/bin/python3
import htmlgen

# Declarations for use later
# anything declared here will be in scope for later make.py files
# as well as <python> tags in .data files

# intializes the library
htmlgen.init(sys.argv, destination='/directory/of/output/website') 
# Cleans the destination directory
htmlgen.clean() 
# Reads .data files and processes code between <python> </pathon> tags
htmlgen.pages_from_datafiles(globals()) 
# Runs makefiles contained in any subdirectories
htmlgen.run_make_subdirs(globals()) 
```

### Basic webpages
The other make.py files should generally look somthing like just:
```
htmlgen.pages_from_datafiles(globals())
htmlgen.run_make_subdirs(globals())
```
Note that pages_from_datafiles also has a side-effect of creating symlinks in the destination directory for everything that's not a ".data" file in the source directory. So, for example, I use this line in my "css" directory even though there are no datafiles there.

### Indexing
Another useful line is:

> simple_index(gen_header, gen_footer, gen_title) 

This will index the entire hierarchy of directories under this file (no need to put make.py's there). And create a set of pages linking to them. This is useful for archies of scripts, music, or whatever. So you don't have to link to each one manually

You can define gen_header(title, path) gen_footer(title, path) and gen_title(title, date, link=None, path=None) in your top level make.py. "title" for header and footer is simply the title of the path. Path is the relative path in your website to where the .html page being generated is located. This path is useful for links in the header, footer, or title of a webpage. "htmlgen.computeurl()" takes a path and a relative link. If you use it correctly you can use relative paths so links work properly when filed using "file:///" making website development easier.

### Blog generation
Don't forget that python has closures. You can do your own computation and grab the results in your closure when you define gen_header, gen_footer, and gen_title.

For a blog you can use something like this:

> blog_list = htmlgen.bloglist_from_files()
> htmlgen.bloglist_ammend_data(blog_list, globals())
> htmlgen.bloglist_dump_posts(gen_blog_header, gen_blog_footer, gen_title, blog_list)
> htmlgen.bloglist_dump_rss(main_site_link, 'NameOfBlog', 'A description of what this blog is about', blog_list[:20], gen_title)
> htmlgen.bloglist_dump_blog(gen_blog_header, gen_blog_footer, gen_title, blog_list)

The first line reads all of the ".blog" files in the directory and parses them in to a list of dictionaries called "blog_list". This includes the names of the files, titles of the documents, relative links, etc. Note that ".blog" files are named using an ISO 8601 date followed by an underscore, the title of the page, and finishing with ".blog"

I capture "blog_list" in my gen_footer() closure so I can use it to create a sidebar with links to all of the blog posts.

> htmlgen.bloglist_ammend_data(blog_list, globals())

Takes "blog_lists" and adds in a "data" field to each entry with the complete contents of the .blog file, including the rsults of running any <python> tags. Obviously for extremely large blogs this may be an issue. It's fine in the hundreds of posts range, but this would need to be refactored for a large commercial blog.

> htmlgen.bloglist_dump_posts(gen_blog_header, gen_blog_footer, gen_title, blog_list)

Writes out individual pages for every blog post in blog_list. Note that this needs to come after a call to "ammend_data". 

> htmlgen.bloglist_dump_rss(main_site_link, 'NameOfBlog', 'A description of what this blog is about', blog_list[:20], gen_title)

Writes out an "rss.xml" file containing the most recent 20 posts. Note that at the moment this includes the content as well. If you want to keep the content a secret you'll need to edit the library.

> htmlgen.bloglist_dump_blog(gen_blog_header, gen_blog_footer, gen_title, blog_list)

This function does make some actual decisions for you. I considered not including it for that reason, but it's too useful, and the decisions are very minor. I found myself copying this code from one blog to another myself, so I included it.
This function paginates your entire blog in to pages with some number of links on them. In the process it also generates "next" and "prev" links to navigate this pagination. It uses "gen_title" to make a title for each post splitting posts with a horizantal line (<hr> tag).
If this function doesn't meet your needs for some reason you can obviously write your own and the code will provide you a helpful outline. 

### How I use it
I use this library by writing "def gen_header(title, path)" in my top make.py. Then I place <python> generate_header(title, date) </python> at the begining of each path and similar for the footer at the end. This way I always get consistant pages, and only have to write that code once and all my pages look similar. For more details on exact use etc. see htmlgen.py docstrings. For an example website built using htmlgen see "https://www.smalladventures.net"

This library also contains a couple other scripts:

- google_to_blog.py is a script I used to convert the XML files I downloaded from google in to my blog when moving off blogger. It's not flawless (for example, it finds drafts, not just published content), but you may find it useful.
- new_blog_post.sh is a trivial shell script that, given a blog title will generate the file containing it using the current time as the time as the "posted" time. I use this to start a new blog post.
- extract_flickr_ids.py is a script I wrote to pull flickr ids out of all of my blog posts. This way I could identify which images are being used so I could potentially migrate off flickr (I actually deleted everything *else* on flickr instead, at least for now). Like google_to_blog.py, if you're migrating your blog this may be useful.
