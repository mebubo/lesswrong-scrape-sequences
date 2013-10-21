from lxml.html import builder as E

class Sequence(object):
    def __init__(self, title, number):
        self._title = title
        self._number = number
        self._entries = []
    
    def has_posts(self):
        return len(self._entries)
    
    def filename(self):
        return self._entries[0].filename
    
    def title(self):
        return self._title

    def full_title(self):
        return "Sequence {:02d}: {}".format(self._number, self._title)
    
    def append(self, p):
        self._entries.append(p)
    
    def before(self, p):
        ix = self._entries.index(p)
        if ix == 0:
            return None
        return self._entries[ix -1]
    
    def after(self, p):
        ix = self._entries.index(p)
        if ix+1 == len(self._entries):
            return None
        return self._entries[ix +1]

    def filename(self):
        return "seq{:02d}.html".format(self._number)

    def __iter__(self):
        for p in self._entries:
            yield p

    def a(self):
        return E.A(self.full_title(), href=self.filename())

    def li(self):
        return E.LI(self.a())
