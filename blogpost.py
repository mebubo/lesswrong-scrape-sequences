import os
import re
import urllib2
import urlparse
import lxml.html
from lxml.html import builder as E

import cachefetch
import substable

#allattrs = set()

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
    
def urltocode(url):
    purl = urlparse.urlparse(url)
    if purl.hostname != "lesswrong.com":
        return None
    path = purl.path.split("/")
    if path[0] == "" and path[1] == "lw":
        return path[2]
    elif path[:4] == ["", "r", "lesswrong", "lw"]:
        return path[4]
    return None

def get_title(content):
    for t in content.xpath("//h1/a/text()"):
        return unicode(t).strip()

def get_body(content, code):
    for frag in content.xpath("//div[@id=\"entry_t3_{0}\"]/div/div".format(code)):
        return frag
    return None

def get_date(content):
    for frag in content.xpath("//span[@class=\"date\"]/text()"):
        return unicode(frag)
    return None

def get_titleurl(content):
    for a in content.xpath("//h1/a/@href"):
        return unicode(a)

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
        self.code = urltocode(url)
        self.filename = "{0:04d}.html".format(sequence)
        self.backrefs = set()
        self.sequences = []
        
    def __cmp__(self, o):
        return cmp(self.sequence, o.sequence)
    
    def urljoin(self, frag):
        return urlparse.urljoin(self.url, frag)
    
    def get_nexturl(self):
        if self.code == "t6":
            # A 500 error
            return "http://lesswrong.com/lw/t7/dumb_deplaning/"
        elif self.code == "2s":
            # Points to the article logically after it for some reason
            return "http://lesswrong.com/lw/31/what_do_we_mean_by_rationality/"
        doc = cachefetch.get_from_url(
            "http://lesswrong.com/api/article_navigation?article_id={0}".format(self.code))
        li = get_li(doc, "by author")
        if li is None: return None
        ahref = get_ahref(li, "Next")
        if ahref is None: return None
        return self.urljoin(ahref)
            

    def read(self):
        content = cachefetch.get_html_from_url(self.url)
        self.url = self.urljoin(get_titleurl(content))
        self.title = get_title(content)
        self.date = get_date(content)
        self.entry = get_body(content, self.code)
        for e in self.entry.iter():
            #allattrs.add(e.tag)
            #for k in e.attrib.iterkeys():
            #    allattrs.add(e.tag + "/" + k)
            for k in ("class", "dragover"):
                if e.attrib.has_key(k):
                    del e.attrib[k]
            e.text = hifroz(e.text)
            e.tail = hifroz(e.tail)

    def filename_for_image(self, url, content):
        extension = url[url.rindex("."):]
        if extension.lower() not in [".gif", ".png", ".svg", ".jpg", ".jpeg"]:
            extension = ""
        return "{0}{1}".format(cachefetch.sha1(content)[:8], extension)

    def fix_urls(self, codemap):
        for img in self.entry.xpath(".//img"):
            if not img.attrib.has_key("src"):
                continue
            iurl = self.urljoin(img.attrib["src"])
            print " -image-", iurl
            content = cachefetch.read_url(iurl)
            name = self.filename_for_image(iurl, content)
            img.attrib["src"] = name
            print "Writing", name, iurl
            with open("target/" + name, "w") as f:
                f.write(content)
        for a in self.entry.xpath(".//a"):
            if not a.attrib.has_key("href"):
                continue
            href = self.urljoin(a.attrib["href"])
            if href.startswith("http://www.overcomingbias.com/"):
                href = cachefetch.check_for_301(href)
            code = urltocode(href)
            # insert link url in plaintext after the link
            a.tail = u" [{0}]{1}".format(href, a.tail if a.tail else "")
            if code is not None and code in codemap and code != self.code:
                ref = codemap[code]
                a.attrib["href"] = ref.filename
                ref.backrefs.add(self)
            else:
                a.attrib["href"] = href
                #if code is not None:
                #    print "????", href

    def addseq(self, seq):
        self.sequences.append(seq)

    def ahref(self):
        return E.A(self.title, href=self.filename)

    def li(self, include_date=True):
        return E.LI(self.ahref(), (", " + self.date) if include_date else "")

    def link_post_or_sequence(self, post, sequence, label):
        if post is not None:
            return E.P(E.I(label), E.A(post.title, href=post.filename))
        elif sequence is not None:
            return E.P(E.I(label), sequence.a())
        else:
            return ""

    def write(self):
        if len(self.backrefs) == 0:
            refs = []
        else:
            refl = [e for p in sorted(self.backrefs)
                for e in (u" \u2022 ", p.ahref())]
            refl[0] = E.I("Referenced by: ") #ugh
            refs = [E.P(*refl)]

        seqs = [E.TABLE(
            E.TR(E.TH(seq.a(), ":", colspan="2")),
            E.TR(
                E.TD(self.link_post_or_sequence(seq.before(self), seq.previous, "Previous: ")),
                E.TD(self.link_post_or_sequence(seq.after(self), seq.next, "Next: "))
            )
        ) for seq in self.sequences]
        page = E.HTML(
            E.HEAD(
                E.TITLE(self.title)
            ), E.BODY(*([
                E.H1(self.title),
                E.P(E.I("Eliezer Yudkowsky, " + self.date)),
                ] + list(self.entry) + [E.HR()] + seqs + refs + [
                E.P(E.I("Original with comments: "),
                    E.A(self.title, href=self.url))
            ]))
        )

        with open("target/" + self.filename, "w") as f:
            f.write(lxml.html.tostring(page))


