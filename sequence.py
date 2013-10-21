import lxml
from lxml.html import builder as E

class Sequence(object):
    def __init__(self, title, number):
        self._title = title
        self._number = number
        self._entries = []
        self.previous = None
        self.next = None

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

    def write(self):
        if self.has_posts():
            with open("target/" + self.filename(), "w") as f:
                f.write(lxml.html.tostring(
                    E.HTML(
                        E.HEAD(
                            E.TITLE(self.full_title()),
                        ), E.BODY(
                            E.H1(self.full_title()),
                            E.UL(*[p.li(include_date=False) for p in self]),
                            *self.sequence_navigation()
                        )
                    )
                ))


    def sequence_navigation(self, link_index=True):
        if link_index:
            yield E.P(E.I("Sequence index: "), E.A("All sequences", href="sequences.html"))
        if self.previous is not None:
            yield E.P(E.I("Previous sequence: "), self.previous.a())
        if self.next is not None:
            yield E.P(E.I("Next sequence: "), self.next.a())


class SequenceList(object):

    def __init__(self):
        self._list = []

    def add(self, sequence):
        if len(self._list) > 0:
            previous = self._list[-1]
            previous.next = sequence
            sequence.previous = previous
        self._list.append(sequence)

    def __iter__(self):
        for s in self._list:
            yield s

    def write(self):
        print "Writing sequence index"
        with open("target/sequences.html", "w") as f:
            f.write(lxml.html.tostring(
                E.HTML(
                    E.HEAD(
                        E.TITLE("All sequences"),
                    ), E.BODY(
                        E.H1("All sequences"),
                        E.UL(*[E.LI(E.B(s.full_title()),
                                    E.UL(*[p.li(include_date=False) for p in s]))
                               for s in self
                               if s.has_posts()])
                    )
                )))
        print "Writing sequences"
        for s in self:
            s.write()

    def save(self):
        with open("sequences.org", "w") as f:
            for s in self:
                f.write("* {0}\n".format(s.title()))
                for p in s:
                    f.write("  - {0}\n".format(p.url))
                f.write("\n")

