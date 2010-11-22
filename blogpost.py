import os
import re
import urllib
import urlparse
import lxml.html
from lxml.html import builder as E

import cachefetch
import substable

subsmap = dict((k, v)
    for k, v in substable.substable
    if v is not None)

def get_place(li):
    for sp in li.xpath("span[@class=\"place\"]/text()"):
        return sp
    return None

def get_li(doc, place):
    for li in doc.xpath("li"):
        if get_place(li) == place:
            return li
    return None    

def get_ahref(li, alt):
    for a in li.xpath("a[@class=\"nav\"]"):
        for imgalt in a.xpath("img/@alt"):
            if imgalt == alt:
                return unicode(a.attrib["href"])
    return None
    
def goodpath(path):
    return (len(path) == 5
        and path[0] == ""
        and path[1] == "lw"
        and path[4] == "")

def get_title(content):
    for t in content.xpath("//h1/a/text()"):
        return unicode(t)

def get_body(content, code):
    for frag in content.xpath("//div[@id=\"entry_t3_{0}\"]/div/div".format(code)):
        return frag
    return None

def get_date(content):
    for frag in content.xpath("//span[@class=\"date\"]/text()"):
        return unicode(frag)
    return None

rexp = re.compile(r"([ -~]*)([^ -~]+|$)")
def hifroz(t):
    if t is None:
        return None
    # Pretty convinced that none of these are semantic
    offset = 0
    res = []
    while offset < len(t):
        m = rexp.match(t, offset)
        u = m.group(2)
        res += [m.group(1), subsmap.get(u, u)]
        offset = m.end()
    return "".join(res)

class Blogpost(object):
    def __init__(self, sequence, url):
        self.sequence = sequence
        self.url = url
        path = urlparse.urlparse(url).path.split("/")
        assert(goodpath(path))
        self.code = path[2]
        #self.filename = "/".join(path[1:-1]) + ".html"
        #self.dir = "/".join(path[1:-2])
        self.filename = "{0:04d}.html".format(sequence)
        self.backrefs = set()
    
    def get_nexturl(self):
        if self.code == "t6":
            return "http://lesswrong.com/lw/t7/dumb_deplaning/"
        doc = cachefetch.get_from_url(
            "http://lesswrong.com/api/article_navigation?article_id={0}".format(self.code))
        li = get_li(doc, "by author")
        if li is None: return None
        ahref = get_ahref(li, "Next")
        if ahref is None: return None
        return urlparse.urljoin(self.url, 
            urllib.quote(ahref.encode("utf-8")))

    def read(self):
        content = cachefetch.get_html_from_url(self.url)
        self.title = get_title(content)
        self.date = get_date(content)
        self.entry = get_body(content, self.code)
        for e in self.entry.iter():
            e.text = hifroz(e.text)
            e.tail = hifroz(e.tail)

    def fix_urls(self, urlmap):
        for a in self.entry.xpath(".//a"):
            if not a.attrib.has_key("href"):
                continue
            href = urlparse.urljoin(self.url, a.attrib["href"])
            if href.startswith("http://www.overcomingbias.com/"):
                href = cachefetch.check_for_301(href)
            if href in urlmap:
                ref = urlmap[href]
                a.attrib["href"] = ref.filename
                ref.backrefs.add(self)
            else:
                a.attrib["href"] = href

    def li(self):
        return E.LI(E.A(self.title, href=self.filename), ", ", self.date)

    def write(self):
        if len(self.backrefs) == 0:
            refs = []
        else:
            refs = [           
                E.P(E.I("Referenced by:")),
                E.UL(*[p.li()
                    for p in sorted(self.backrefs, 
                        key=lambda p: p.sequence)])
            ]

        page = E.HTML(
            E.HEAD(
                E.TITLE(self.title)
            ), E.BODY(*([
                E.H1(self.title),
                E.P("Eliezer Yudkowsky, " + self.date),
                ] + list(self.entry) + refs + [
                E.P(E.I("Original with comments: ", 
                    E.A(self.title, href=self.url)))
            ]))
        )

        with open("target/" + self.filename, "w") as f:
            f.write(lxml.html.tostring(page))

def write_title(posts):
    with open("target/index.html", "w") as f:
        f.write(lxml.html.tostring(
            E.HTML(
                E.HEAD(
                    E.TITLE("Eliezer Yukowsky blog posts, 2006-2010"),
                ), E.BODY(
                    E.H1("Eliezer Yukowsky blog posts, 2006-2010"),
                    E.UL(*[p.li() for p in posts])
                )
            )))

def scrape_all(start_url, sequencer):
    print "Collecting URLs"
    posts = []
    url = start_url
    for seq in sequencer:
        print "...", url
        post = Blogpost(seq, url)
        posts.append(post)
        url = post.get_nexturl()
        if url is None:
            break

    print "Reading articles"
    for i, post in enumerate(posts):
        print "{0:3}/{1:3} {2}".format(i+1, len(posts), post.url)
        post.read()

    print "Fixing URLs"
    urlmap = dict((p.url, p) for p in posts)
    for post in posts:
        post.fix_urls(urlmap)

    print "Writing"
    for post in posts:
        post.write()

    print "Writing title"
    write_title(posts)
    print "Done"

