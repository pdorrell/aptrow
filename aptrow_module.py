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
        yield "<p>Information about the Aptrow application"
        yield "<h2>Resource modules</h2><ul>"
        for prefix, resourceModule in resourceModules.items():
            yield "<li><a href=\"%s\">%s</a></li>" % (ResourceModuleResource(prefix).url(), 
                                                                          h(prefix))
        yield "</ul>"
        
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
        yield "<p>Information about Aptrow resource module %s</p>" % self.prefix
        resourceModule = resourceModules[self.prefix]
        yield "<h2>Resource types</h2>"
        yield "<table><thead><tr><td>Type</td><td>Python Class</td></tr></thead>"
        yield "<tbody>"
        for resourceType, resourceClass in resourceModule.classes.items():
            yield "<tr><td><a href=\"%s\">%s</a></td><td>%s</td></tr>" % (ResourceTypeResource(self.prefix, resourceType).url(), 
                                                                          h(resourceType), h(resourceClass.__name__))
        yield "</tbody></table>"

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
        yield "<p>Information about Aptrow resource type %s</p>" % self.type
        resourceModule = resourceModules[self.prefix]
        resourceClass = resourceModule.classes[self.type]
        params = resourceClass.resourceParams
        yield "<p>Resource parameters:<ul>"
        for param in params:
            yield "<li>%s</li>" % param.description()
        yield "</ul></p>"
