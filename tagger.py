import re
from collections import defaultdict
import logging
import os
import itertools
import argparse


def generate_indices(folder, threshhold=2):
    """
    Generates a tag list for a folder full of mardkown files, based on a weighted associative token search.

    taglist.txt
    --------------
    The actual tags are found in the file taglist.txt. Each line in the file is a comma separated list of search terms
    (lower cased) with the tag as the first item.  Items with variant, such as plural or adjectival forms, can be
    specified with square brackets, so assyria[n]  will look for both 'assyria' and 'assyrian'. If a search term is
    a phrase, enclose it in quotes ("roman republic"). Very common words like "a" and "the" are prefiltered for speed,
    so for "alexander the great" you would use "alexander great".

    tags can include other tags. In the parent tag include the child prefixed by a plus.  Thus:

        sparta, spartan[s], lacedaemon[ian], ....
        greece, +athens, +sparta, greek, hellenic, ...

    will make sure the everything tagged 'sparta' is also tagged 'greece.'  The child tag should be defined before the parent,
    as in the example here.

    lines in `taglist.txt` beginning with # will be ignored.

    associations
    --------------
    The tagging is associative, that is, for a text to be tagged it needs to have more than one of the keywords in tags.txt.
    By default, tags are applied if two keywords are present; you can change this by passing a different value as the
    `threshold` argument. The right value will depend on the nature of your tags, but generally setting this to one will generate
    a lot of false positives and is probably not helpful.

    output
    -----
    Running this generates index files in the same folder as the markdown.  There will be one index file for each tag in
    taglist.text and for each year in the head matter of the markdown files. It will also generate am index of all tags
    (in "index_tags.md") and an index of all years (in "index_years.md")
    """

    FOLDER = os.path.normpath(folder)
    assert os.path.exists(FOLDER), f"folder '{FOLDER}' does not exist"

    # higher numbers require more hits on more tags,
    # lower numbers will favor the combination tags. A value larger than 1
    # is good to avoid single-word mentions applying a tag
    THRESHOLD = threshhold

    logger = logging.getLogger("tagger")
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    tagdict = {}
    phrasedict = {}
    hierarchydict = {}
    years = defaultdict(list)

    def parse_taglist():
        counter = 0
        with open("taglist.txt", "rt") as taglist:
            for line in taglist:
                counter += 1
                if len(line) < 2 or line.startswith("#"):
                    continue
                tokens = [i.strip() for i in line.split(",")]
                headword, *rest = tokens
                tagdict[headword] = headword
                hierarchydict[headword] = []
                for r in rest:
                    # a leasing plus means "this tag is part of that tag"
                    # eg "+babylon" in "mesopotamia" means "anything tagged 'babylon'
                    # also gets mesopotamia"
                    if r.startswith("+"):
                        hierarchydict[r[1:]].append(headword)
                        continue

                    # multi-word cues are included w
                    if r.startswith('"'):
                        assert r.endswith('"'), f"malformed quote in line {counter}"
                        phrasedict[tuple(r[1:-1].split())] = headword
                        continue

                    # word[ending] generates variants
                    if "[" in r or "]" in r:
                        assert (
                            "[" in r and "]" in r
                        ), f"malformed ending in line {counter}"
                        caret = r.index("[")
                        tagdict[r[:caret]] = headword
                        cleaned = r.replace("[", "").replace("]", "")
                        tagdict[cleaned] = headword
                        continue

                    # or just add it
                    tagdict[r] = headword

    IGNORE = set()
    with open("ignore_words.txt", "rt") as ignorefile:
        for line in ignorefile:
            IGNORE.add(line.strip())

    def extract_lexemes(filename):
        with open(filename, "rt", encoding="utf-8") as thefile:
            for line in thefile:
                if line.strip().startswith("written"):
                    date = line.partition(":")[-1].strip()
                    date = date.split("-")[0]
                    yfile = os.path.relpath(filename, FOLDER)
                    years[date].append(yfile)
                    break

        with open(filename, "rt", encoding="utf-8") as thefile:
            title_tokens = iter(
                os.path.basename(os.path.splitext(filename)[0]).lower().split("-")
            )

            raw_words = itertools.chain(
                iter(thefile.read().replace("\u200b", " ").split()), title_tokens
            )
            remove_urls = (re.sub("\(.*\)", "", t) for t in raw_words)
            remove_quora_links = (t for t in remove_urls if not t.startswith("/"))
            remove_numbers = (re.sub("[\d]", "", t) for t in remove_quora_links)
            lowered = (t.lower() for t in remove_numbers)
            fix_quotes = (re.sub("[’'‘]", "'", t) for t in lowered)
            depunctuated = (re.sub("[\?\.\!\,—;:]…", "", t) for t in fix_quotes)
            dispossed = (re.sub("([’'][st])", "", t) for t in depunctuated)
            unformattes = (re.sub("[\W]", "", t) for t in dispossed)
            no_underscores = (re.sub("[_]", "", t) for t in unformattes)

            return set(no_underscores).difference(IGNORE)

    def tag_file(filename):
        lexemes = extract_lexemes(filename)

        logger.info(f"{os.path.basename(filename)}\n    lexemes: {len(lexemes)}")
        keywords = defaultdict(int)

        for eachtag in tagdict:
            if eachtag in lexemes:
                head = tagdict[eachtag]
                keywords[head] += 1

        for k, v in phrasedict.items():
            if all(item in lexemes for item in k):
                keywords[v] += 1

        results = set()
        for k, v in keywords.items():
            if v > THRESHOLD:
                results.add(k)

        originals = [r for r in results]
        for t in originals:
            for j in hierarchydict.get(t, []):
                results.add(j)

        logger.info(f"   {tuple(results)}")
        return results

    # tag: [list of files matching tag]
    files_per_tag = defaultdict(list)
    # file: [tags]
    tags_per_file = {}

    def tag_folder(folderpath):

        for root, _, files in os.walk(folderpath):

            folderpath = os.path.normpath(os.path.abspath(folderpath))

            for f in files:
                f = f.lower()
                if f.startswith("tag_") or f.startswith("year_"):
                    continue
                if f in ("topics.md", "readme.md"):
                    continue
                if not f.endswith(".md"):
                    continue

                fullpath = os.path.normpath(os.path.join(root, f))
                shortpath = os.path.relpath(fullpath, folderpath)
                file_tags = tag_file(fullpath)
                tags_per_file[shortpath] = file_tags
                for t in file_tags:
                    files_per_tag[t].append(shortpath)

    parse_taglist()
    tag_folder(FOLDER)

    # generate tag indices
    for eachtag in files_per_tag:
        safename = eachtag.replace(" ", "-")
        filename = os.path.normpath(os.path.join(FOLDER, f"tag_{safename}.md"))
        with open(filename, "wt") as tagindex:
            tagindex.write(f"# {eachtag}\n")
            tagindex.write(f"{len(files_per_tag[eachtag])} items\n")
            tagindex.write("\n")
            for eachfile in files_per_tag[eachtag]:
                prettyname = os.path.splitext(os.path.basename(eachfile))[0]
                prettyname = prettyname.split("\\")[-1]
                prettyname = prettyname.replace("-", " ").title()
                prettyname += "?"
                eachfile = eachfile.replace("\\", "/")
                tagindex.write(f"* [{prettyname}]({eachfile})\n")
            logger.info(f"wrote tag {eachtag}")

    # generate year files
    for year in sorted(years.keys()):
        file_list = sorted(years[year])
        filename = os.path.normpath(os.path.join(FOLDER, f"year_{year}.md"))
        with open(filename, "wt") as yearindex:
            yearindex.write(f"# {year}\n")
            yearindex.write(f"{len(years[year])} items\n")
            yearindex.write("\n")
            for eachfile in file_list:
                prettyname = os.path.splitext(os.path.basename(eachfile))[0]
                prettyname = prettyname.split("\\")[-1]
                prettyname = prettyname.replace("-", " ").title()
                prettyname += "?"
                yearindex.write(f"* [{prettyname}]({eachfile})\n")
            logger.info(f"wrote year {year}")

    year_index_file = os.path.normpath(os.path.join(FOLDER, f"index_years.md"))

    with open(year_index_file, "wt") as yearindex:
        yearindex.write(f"# Articles by year\n")
        yearindex.write(f"{len(years[year])} items\n")
        yearindex.write("\n")
        for year in sorted(years.keys()):
            yearindex.write(f"* [{year}](year_{year}.md) ({len(years[year])})\n")

    tag_index_file = os.path.normpath(os.path.join(FOLDER, "index_tags.md"))
    with open(tag_index_file, "wt") as tagindex:
        tagindex.write(f"# Tagged articles\n")
        tagindex.write(f"{len(files_per_tag)} items\n")
        tagindex.write("\n")
        for eachtag in sorted(files_per_tag.keys()):
            safename = eachtag.replace(" ", "-")
            tagindex.write(
                f'* ["{eachtag.title()}"](tag_{safename}.md) ({len(files_per_tag[eachtag])})\n'
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Generate indices for a folder full of markdown files",
        usage=generate_indices.__doc__,
    )
    parser.add_argument("folder", metavar="FOLDER", help="path to markdown folder")
    args = parser.parse_args()
    generate_indices(args.folder)
