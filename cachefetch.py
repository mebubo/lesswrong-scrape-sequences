import os
import base64
import httplib
import urllib
import urllib2
import urlparse
import lxml.etree
import lxml.html
import hashlib

def makedirs(t):
    if not os.path.isdir(t):
        os.makedirs(t)

def deunicode(url):
    purl = urlparse.urlsplit(url)
    p8 = purl.path.encode("utf-8")
    if purl.path == p8:
        return url
    return urlparse.urlunsplit((
        purl.scheme,
        purl.netloc,
        urllib.quote(p8),
        purl.query,
        purl.fragment))


def sha1(content):
    h = hashlib.sha1()
    h.update(content)
    return h.hexdigest()

# Very very simple memoize suitable only for these exact circumstances
# EVIL HACK: fixes Unicode in URLs
def memoize(dr):
    def memf(func):
        def memoized(url):
            url = deunicode(url)
            makedirs("cache/{0}".format(dr))
            basename = base64.b64encode(url, "_-")
            # don't exceed max filename length
            # we don't hash everything to preserve reversibility for most urls
            if len(basename) > 255:
                basename = sha1(url)
            centry = "cache/{0}/{1}".format(dr, basename)
            if os.path.isfile(centry):
                with open(centry) as f:
                    return f.read()
            res = func(url)
            with open(centry, "w") as f:
                f.write(res)
            return res
        return memoized
    return memf
            
# This respects http_proxy
@memoize("urlcontent")
def read_url(url):
    print "Getting: ", url
    return urllib2.urlopen(url).read()

conmap = {}

@memoize("301")
def check_for_301(url):
    print "Checking for 301: ", url
    # workaround for messed up unicode in this redirect
    if url == "http://www.overcomingbias.com/2008/08/lobs-theorem.html":
        return "http://lesswrong.com/lw/t6/the_cartoon_guide_to_Lobs_theorem/"
    purl = urlparse.urlparse(url)
    if purl.hostname not in conmap:
        conmap[purl.hostname] = httplib.HTTPConnection(purl.hostname)
    conn = conmap[purl.hostname]
    conn.request("HEAD", url)
    resp = conn.getresponse()
    try:
        if resp.status == 301:
            return resp.getheader('location')
        else:
            return url
    finally:
        resp.read()

def get_from_url(url):
    return lxml.etree.fromstring(read_url(url))

def get_html_from_url(url):
    return lxml.html.fromstring(read_url(url))


