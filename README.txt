# quoradl
### A Quora backup tool

This is another entry in the how-do-I-archive-my-Quora-answers sweepstakes.  It will download individual answers or do a bulk download. The answers are saved in [Markdown](https://www.markdownguide.org/getting-started/) format for simplicity -- you won't get a full version of the orignal Quora styles, but you will be able to convert these to HTML using any number of tools (converters available [here](https://www.markdownguide.org/tools/))

## Prerequisites

This is a single-file script.  It depends on [html-requests](https://docs.python-requests.org/projects/requests-html/en/latest/) and [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).  If you use [pipenv](https://pipenv.pypa.io/en/latest/) you can use the included Pipfile to install the (the `Pipfile.lock` contains the versions against which this has been tested).  Othewise, `pip install requests-html` and `pip install bs4` should do the trick. 

## Basics

For individual answers you can grab them quite simply, using a quora relative URL:

    python quoradl.py download /What-is-Aristotle-1802/answer/Steve-Theodore

Full URLs and shortened https://qr.ae links also work.


## Scraping

Unfortunately, getting an answer list so you can do a bulk download is highly manual -- Quora seems to make it difficult on purpose.  Effectively the only way to get the list is to get your browser to scroll through all of your answers and then copy-paste the runtime HTML into a text file so you can extract the links from there.

This method has been tested with Chrome, should probably have analogues in other browsers:

1) Go to `your content` (this won't work on _other_ people's content)
2) Scroll down until you get to your first answer (they're sorted in reverse chronological order by default)
3) Right click on a blank space in the window and choose "Inspect" or use Ctrl + Shift + I
4) In the inspect pane which just opened, right click on the first <html> tag and choose Copy > Copy Element
5) Paste the copied text into a utf-8 text file and save it
6) Run this script with the name of the text file as an argument, ie

       python quoradl.py scrape my_answers_file.html

## More help

* The `download` command has a `--output` option so you can specify an output file name.
* The `scrape` command has a `--folder` option so you can direct bulk output to a particular folder
* The `howto` command prints  a copy of the above instructions for Scraping

## Final note

This is intended for fellow authors who want to save their own content.  If you are downloading other people's answers please respect their copyright and their NOT FOR REPRODUCTION flags (if those are present, they are included in the front matter of the markdown files)