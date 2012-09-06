from __future__ import print_function
import os
import pickle
import sys
import urllib2

from lxml import etree
from lxml.builder import E

sys.path.append('.')

import info

url = "http://alerts.weather.gov/cap/us.php?x=1"

def fix_nsmap(nsmap, default='atom'):
    # xpath doesn't like empty namespaces
    try:
        nsmap[default] = nsmap.pop(None)
    except KeyError:
        pass
    return nsmap


class AlertException(Exception):
    pass


class AlertExpired(AlertException):
    pass


class AlertEmpty(AlertException):
    pass


class FeedParser(object):
    """
    Parses the atom feed from the NWS
    """
    def __init__(self):
        try:
            with open('weatherman.log', 'rb') as f:
                self.__log = pickle.load(f)
        except IOError:
            self.__log = []
    
    def __del__(self):
        with open('weatherman.log', 'wbc') as f:
            pickle.dump(self.__log, f)

    def fetch(self, url):
        """
        Return the feed in the url as an lxml etree
        """
        self.feed = etree.XML(urllib2.urlopen(url).read())
        self.nsmap = fix_nsmap(self.feed.nsmap)

    def log(self, alert):
        """
        Insert the given alert into the log, if not yet seen.
        If the insert is successful, return True, else False.
        """
        if alert.ID in self.__log:
            return False
        else:
            self.__log.append(alert.ID)
            return True

    def iter_alerts(self):
        """
        Return alert objects for each entry in feed
        """
        self.entries = self.feed.xpath('//atom:entry[cap:category="Met"]', namespaces=self.nsmap)
        for e in self.entries:
            try:
                a = Alert(e)
                if self.log(a):
                    a.fetch()
                    yield a
            except AlertException:
                pass
        
        
class Alert(object):
    """
    Represents a NWS Alert.
    """
    ID = ""
    cap = None
    certainty = ""
    description = ""
    entry = None
    event = ""
    eventcode = ""
    FIPS6 = []
    headline = ""
    instruction = ""
    note = ""
    nsmap = {'ha': 'http://www.alerting.net/namespace/index_1.0',
             'cap': 'urn:oasis:names:tc:emergency:cap:1.1',
             'atom': 'http://www.w3.org/2005/Atom'}
    severity = ""
    UGC = []
    urgency = ""
    url = ""


    def __init__(self, entry=None, filename=None):
        """
        Initialize from an ATOM entry or a file
        """
        if entry is not None:
            self.entry = entry
        elif filename is not None:
            self.load(filename)
        self.parse_entry()
        
    def __repr__(self):
        return self.ID

    def fetch(self):
        """
        Fetch the full alert
        """
        self.cap = etree.XML(urllib2.urlopen(self.url).read())

    def dump(self, filename=None):
        """
        Save the data for later
        """
        if filename is None:
            filename = 'CAP_%s.xml' % self.ID
        with open(filename, 'wbc') as f:
            data = self.dumps()
            f.write(data)
        return filename

    def dumps(self):
        """
        Dump alert to an XML string for serialization.
        """
        doc = E.alertitem(self.entry, self.cap)
        return etree.tostring(doc, pretty_print=True)

    def load(self, filename):
        """
        Load alert from a file.
        """
        with open(filename,'rb') as f:
            self.loads(f.read())

    def loads(self, xml_string):
        """
        Load alert from a string.
        """
        doc = etree.XML(xml_string)
        self.entry = doc[0]
        self.cap = doc[1]
            
    def parse_entry(self):
        """
        Extract available data from the entry object.
        """
        ID = self.entry.xpath('atom:id/text()', namespaces=self.nsmap)[0]
        self.ID = ID.split('x=')[-1]
        self.url = self.entry.xpath('atom:link/@href', namespaces=self.nsmap)[0]

        self.status = self.entry.xpath('cap:status/text()', namespaces=nsmap)[0]
        self.category = self.entry.xpath('cap:category/text()', namespaces=nsmap)[0]
        self.urgency = self.entry.xpath('cap:urgency/text()', namespaces=nsmap)[0]
        self.severity = self.entry.xpath('cap:severity/text()', namespaces=nsmap)[0]
        self.certainty = self.entry.xpath('cap:certainty/text()', namespaces=nsmap)[0]
    
        #==================================
        #Determine Regions
        regions = self.entry.xpath("//cap:geocode[atom:valueName='FIPS6' and atom:valueName='UGC']",
                                 namespaces=self.nsmap)[0]
        self.FIPS6 = regions[1].text.split(" ")
        self.UGC = regions[3].text.split(" ")


    def parse(self):
        """
        Parse out the data
        """
        #==================================
        #If we don't have data, raise an exception
        if self.cap is None:
            raise AlertEmpty("Fetch or Load data before parsing!")
        
        #==================================
        #Determine if the alert has expired
        self.note = self.cap.xpath('cap:note', 
                              namespaces=self.nsmap)[0].text
        if self.note.strip() == "This alert has expired":
            raise AlertExpired(self.note)
        
        #==================================
        #Determine Regions
        self.FIPS6 = []
        FIPS6 = self.cap.xpath('cap:info/cap:area/cap:geocode[cap:valueName="FIPS6"]', 
                       namespaces=self.nsmap)
        for r in FIPS6:
            self.FIPS6.append(r[1].text)
        self.UGC = []
        UGC = self.cap.xpath('cap:info/cap:area/cap:geocode[cap:valueName="UGC"]', 
                       namespaces=self.nsmap)
        for r in UGC:
            self.UGC.append(r[1].text)


        #==================================
        #Determine Alert type
        self.event = self.cap.xpath('cap:info/cap:event',
                             namespaces=self.nsmap)[0].text
        
        #==================================
        #Determine Alert severity
        self.severity = self.cap.xpath('cap:info/cap:severity', 
                                       namespaces=self.nsmap)[0].text

        #==================================
        #Get Headline, Description, Instructions
        self.headline = ""
        self.description = ""
        self.instruction = ""
        
        self.headline = self.cap.xpath('cap:info/cap:headline',
                                       namespaces=self.nsmap)[0].text

        self.description = self.cap.xpath('cap:info/cap:description',
                                          namespaces=self.nsmap)[0].text

        #This element is optional (included in most)
        res = self.cap.xpath('cap:info/cap:instruction',
                             namespaces=self.nsmap)
        try:
            self.instruction = res[0].text or ""
        except IndexError:
            pass
        
    def generate_email(self):
        """
        Set up email alert text
        """
        msg = '\n'.join((self.note,
                         self.headline,
                         self.description,
                         self.instruction))
        return msg

    def generate_txt(self, region_number=None, truncate=True):
        """
        Set up txt alert text
        """
        if region_number is None:
            note = self.note
        elif region_number in self.FIPS6:
            region = info.same_by_code[region_number]
            note = 'Alert for %s' % region
        else:
            return
        msg = '\n'.join((note,
                         self.headline))
        if truncate:
            msg = msg[:140]

        return msg


if __name__ == "__main__":
    #Self test
    p = FeedParser()
    p.fetch(url)
    g = p.iter_alerts()
    # a = g.next()
    # a.parse()
    # print(a)
    for a in g:
        try:
            a.parse()
            print(a.generate_txt(a.FIPS6[0]), '\n', len(a.generate_txt(a.FIPS6[0])), '\n')
        except AlertExpired:
            pass
        except Exception as e:
            print(e)
            a.dump()
    print("Done!")
