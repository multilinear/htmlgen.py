htmlgen.py
==========

High flexible html generation library for python - particularly useful for very lightweight development of static content.

I was annoyed at how heavyweight everything I could find was, so sometime ago I wrote some crappy python scripts to help manage my own website. That is ensure common headers and footers and that sort of thing.

Well, after using it for several years and going through a couple of rewrites I decided I should clean it up and publish it, so here it is.

Deps:
There are a couple of dependencies, see htmlgen.py for what to install - it's not much I promise.

Concept:
The idea is simple. It's a directory hierarchy just like you want in your final website. In each directory there's a make.py file. This allows for arbitrary complexity as desired by the user. make.py files inherit context from the make.py file in the parent directory, allowing you to build up a library of useful functions for a portion of your site.

Next there's some supplied functions for taking a ".data" file, which is in essence a .html file, but can contain <python> and </python> tags. The functions will take a .data file and convert it to a .html file. Whatever is between the <python> tags gets interpeted and it's output replaces the tags in the resulting .html file.

Your root "make.py" file should look something like this:

import htmlgen

htmlgen.init(sys.argv)
htmlgen.clean(htmlgen.dest_base, htmlgen.dest_source) # see docs to understand the order here
htmlgen.pages_from_datafiles(htmlgen.curdir, htmlgen.src_base, htmlgen.dest_base, globals())
htmlgen.run_make_subdirs(htmlgen.curdir, htmlgen.src_base, htmlgen.dest_base, globals())

The other make.py files should generally look like this, but only the last two lines. Of course, you may want to do something much more interesting in your make.py files occasionally (I do). This is just the default setup that will interpret .data files through your hierarchy.

For more details on exact use etc. see htmlgen.py


