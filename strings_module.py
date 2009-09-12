""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

from aptrow import *
import htmltags as tag

# Aptrow module presenting a character string (encoded in the URL) as a resource

aptrowModule = ResourceModule()

@resourceTypeNameInModule("string", aptrowModule)
class String(Resource):
    """A resource representing a String value. (There is no external resource, as the 
    string is provided as a parameter. This resource type is mostly useful for testing, 
    for example to test HTML quoting. But it could have other uses, for example to display
    all the properties of a string, what characters it contains, how long it is, etc.)"""
    
    resourceParams = [StringParam("value")]

    def __init__(self, value):
        Resource.__init__(self)
        self.value = value
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"value": [self.value]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "String: %r" % self.value
    
    def html(self, view):
        """HTML content for string: show it in bold."""
        yield tag.P("String: ", tag.B(h(self.value)))
