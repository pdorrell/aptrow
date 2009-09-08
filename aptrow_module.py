""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

from aptrow import *

# Aptrow module giving access to components of Aptrow itself.

aptrowModule = ResourceModule()
    
@resourceTypeNameInModule("aptrow", aptrowModule)
class AptrowResource(BaseResource):
    """A resource representing the Aptrow application itself"""
    
    resourceParams = []
    
    def __init__(self):
        BaseResource.__init__(self)
    
    def urlParams(self):
        return {}
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Aptrow"
    
    def html(self, view):
        yield tag.P("Information about the Aptrow application")
        yield tag.H2("Resource modules")
        yield tag.UL([tag.LI(tag.A(h(prefix), href = ResourceModuleResource(prefix).url()))
                      for prefix, resourceModule in resourceModules.items()])
        
@resourceTypeNameInModule("module", aptrowModule)
class ResourceModuleResource(BaseResource):
    """A resource representing an Aptrow Module."""
    
    resourceParams = [StringParam("prefix")]
    
    def __init__(self, prefix):
        BaseResource.__init__(self)
        self.prefix = prefix
        
    def urlParams(self):
        return {"prefix": [self.prefix]}
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Aptrow Resource Module %s" % self.prefix
    
    def checkExists(self):
        if self.prefix not in resourceModules:
            raise NoSuchObjectException ("No such Aptrow resource module: %r" % self.prefix)
    
    def html(self, view):
        yield tag.P("Information about Aptrow resource module ", tag.B(self.prefix))
        resourceModule = resourceModules[self.prefix]
        yield tag.H2("Resource types")
        yield tag.TABLE(tag.THEAD(tag.TR(tag.TD("Type"), tag.TD("Python Class"))), 
                        tag.TBODY([tag.TR(tag.TD(tag.A(h(resourceType), 
                                                       href = ResourceTypeResource(self.prefix, resourceType).url())), 
                                          tag.TD(h(resourceClass.__name__)))
                                   for resourceType, resourceClass in resourceModule.classes.items()]), 
                        border = 1)

@resourceTypeNameInModule("resourceType", aptrowModule)
class ResourceTypeResource(BaseResource):
    """A resource representing a resource type"""
    
    resourceParams = [StringParam("prefix"), StringParam("type")]
    
    def __init__(self, prefix, type):
        BaseResource.__init__(self)
        self.prefix = prefix
        self.type = type
        
    def urlParams(self):
        return {"prefix": [self.prefix], "type": [self.type]}
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Aptrow Resource Type %s/%s" % (self.prefix, self.type)
    
    def checkExists(self):
        if self.prefix not in resourceModules:
            raise NoSuchObjectException ("No such Aptrow resource module: %r" % self.prefix)
        resourceModule = resourceModules[self.prefix]
        if self.type not in resourceModule.classes:
            raise NoSuchObjectException ("No such Aptrow resource type: %r in module %s" % (self.type, self.prefix))

    def html(self, view):
        yield tag.P("Information about Aptrow resource type ", tag.B(self.type))
        resourceModule = resourceModules[self.prefix]
        resourceClass = resourceModule.classes[self.type]
        params = resourceClass.resourceParams
        yield tag.P("Resource parameters:", tag.UL([tag.LI(param.description()) 
                                                    for param in params]))

@resourceTypeNameInModule("resource", aptrowModule)
class ResourceResource(BaseResource):
    """A resource representing itself as an Aptrow resource (to allow reflection within Aptrow) """
    resourceParams = [ResourceParam("resource")]
    
    def __init__(self, resource):
        BaseResource.__init__(self)
        self.resource = resource
    
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"resource": [self.resource.url()]}
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Resource [%s]" % self.resource.heading()
    
    @staticmethod
    @interpretationOf(aptrowResource)
    def interpretation(resource):
        return Interpretation(ResourceResource(resource), "reflected", likely = True)
    
    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield tag.P("Reflection information about resource ", tag.B(self.resource.htmlLink()))
        yield self.resource.reflectionHtml()
