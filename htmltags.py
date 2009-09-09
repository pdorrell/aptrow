""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

"""Implementation of a builder-style notation for HTML in Python"""

def toString(data):
    """Return string form of object,  _unless_ it is a tuple or list, in which
    case concatenate string forms of items in the tuple/list."""
    if type(data) in [tuple, list]:
        return "".join([toString(item) for item in data])
    else:
        return str(data)

class Tag:
    """Class representing an HTML tag element. Has name, child elements, and attributes."""
    def __init__(self, tagName, *children, **attributes):
        self.tagName = tagName
        self.children = children
        self.attributes = attributes
        
    def __str__(self):
        """How this tag is output as HTML text."""
        if len(self.children) == 0:
            return self.start(closed = True)
        else:
            return self.start() + toString(self.children) + self.end()
        
    def __repr__(self):
        return str(self)
    
    def start(self, closed = False):
        """Output HTML string for opening tag for this element"""
        if len(self.attributes) == 0:
            attributesString = ""
        else:
            attributesString = " %s" % " ".join(["%s=\"%s\"" % (key, value) 
                                                 for key, value in self.attributes.items()])
        closeSlash = "/" if closed else ""
        return "<%s%s%s>" % (self.tagName, attributesString, closeSlash)
    
    def end(self):
        """Output HTML string for closing tag for this element"""
        return "</%s>" % self.tagName
    
def tagFunction(tagName):
    """Return a function for creating a Tag object with specified name"""
    def func(*children, **attributes): 
        return Tag(tagName, *children, **attributes)
    return func

"""List of HTML tags (incomplete at the moment)"""
htmlTagNames = ["h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "b", "ul", "li", "small", "br", 
                "table", "thead", "tbody", "tr", "tr", "td", 
                "form", "input", "submit"]

"""Define tag functions for names in htmlTagNames (function names 
are capitalized, e.g. UL for <ul> tag)."""
for tagName in htmlTagNames:
    globals()[tagName.upper()] = tagFunction(tagName)
