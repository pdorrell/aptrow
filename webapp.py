""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

# Platform: Python 3.1 (currently being developed on MS Windows)

# SECURITY NOTE: This demo application gives read-only access (to any web client that can access localhost)
# to all files and directories on the local filesystem which can be accessed by the user running the application. 
# So beware.

import urllib
import os
import traceback
import cgi
import io

def h(value):
    """ HTML escape a string value """
    return cgi.escape(value)

def hr(value):
    """ HTML escape %r version of object description """
    return h(value.__repr__())

""" Mapping from resource types """
resourceClasses = {}

def resourceTypeName(name):
    """ Class decorator to define the resource type (i.e. 1st part of URL) 
    for a base resource class, i.e. a class derived from BaseResource. """
    def registerResourceClass(resourceClass):
        print("Registering resource class %s as %r" % (resourceClass.__name__, name))
        resourceClasses[name] = resourceClass
        resourceClass.resourcePath = name
        return resourceClass
    return registerResourceClass

class MessageException(Exception):
    """An exception class whose default string representation is the 'message' attribute."""
    def __str__(self):
        return self.message

class ResourceTypeNotFoundForPathException(MessageException):
    """Thrown when looking up a resource type not registered in resourceClasses."""
    def __init__(self, path):
        self.path = path
        self.message = "No resource type defined for path \"%s\"" % path

def getResource(url):
    """Given a URL, find or create the corresponding resource that the URL represents.
    (The intention is to support remote resources from other Aptrow servers, but currently
    only URL's relative to the local server are supported.)
    
    Even though WSGI functions parse URL's and query parameters for you, this method is needed
    to process URL's included as parameter values in other URL's. """
    
    if url.startswith("/"):
        localUrl = url[1:]
        queryStart = localUrl.find("?")
        if queryStart == -1:
            path = localUrl
            query = None
        else:
            path = localUrl[:queryStart]
            query = localUrl[queryStart+1:]
        resource, view = getResourceAndViewFromPathAndQuery(path, query)
        return resource
    else:
        raise Error("Non-local resource URL's not yet implemented (doesn't start with '/'): %s" % localUrl)
    
class UnknownAttributeException(MessageException):
    """Thrown when an attribute name is not valid."""
    def __init__(self, attribute, resource):
        self.attribute = attribute
        self.resource = resource
        self.message = "No attribute \"%s\" defined for resource [%s]" % (attribute, resource.heading())
    
def getResourceAndViewFromPathAndQuery(path, query):
    """Look up resource object from URL path and query. This includes processing of parameters passed to the
    base resource type, and optionally the processing of attribute parameters, for when one resource is
    defined as an attribute of another. (For example, a FileContents resource is the "contents" attribute
    of a File resource, with additional optional parameter "contentType".) A numbering scheme allows attribute
    lookups to be chained (see AptrowQueryParams for details). 
    """
    queryParams = urllib.parse.parse_qs(query)
    resourceClass = resourceClasses.get(path)
    if resourceClass == None:
        raise ResourceTypeNotFoundForPathException(path)
    aptrowQueryParams = AptrowQueryParams(queryParams)
    object = resourceClass(*getResourceParams(aptrowQueryParams, resourceClass.resourceParams))
    for attribute,params in aptrowQueryParams.attributesAndParams():
        attributeValue = object.resolveAttribute(attribute, params)
        if attributeValue == None:
            raise UnknownAttributeException(attribute, object)
        object = attributeValue
    view = aptrowQueryParams.getView()
    if view == None and object != None:
        view = object.defaultView()
    return object, view
                    
class AptrowApp:
    """The main WSGI Aptrow web application. It accepts the URL representing a resource, finds
    the resource, and then asks the resource to display itself."""
    
    def __init__(self, environ, start_response):
        """WSGI initialiser: save environment and response object"""
        self.environ = environ
        self.start = start_response
        #print ("environ = %r" % environ)
        
    def not_found(self, message):
        """General handler for something not found: currently a message in a plain-text page."""
        self.start('404 Not Found', [('Content-type', 'text/plain')])
        return message
    
    def __iter__(self):
        """Main WSGI method to yield content of requested web page. Looks up resource from URL, 
        and then calls resouce "page" method to render the web page."""
        pathInfo = self.environ['PATH_INFO']
        print ("pathInfo = %r" % pathInfo)
        if pathInfo.startswith("/"):
            pathInfo = pathInfo[1:]
        queryString = self.environ['QUERY_STRING']
        print ("queryString = %r" % queryString)
        try:
            object, view = getResourceAndViewFromPathAndQuery(pathInfo, queryString)
            object.checkExists()
            #msg = "<p>AppClass sez, you requested <strong>%s</strong> with query string <b>%s</b></p>"
            #self.message = msg % (h(pathInfo), hr(queryString))
            self.message = ""
            for text in object.page(self, view): yield text
        except MissingParameterException as exc:
            yield self.not_found("For resource type \"%s\" %s" % (pathInfo, exc.message))
        except UnknownAttributeException as exc:
            yield self.not_found(exc.message)
        except ResourceTypeNotFoundForPathException as exc:
            yield self.not_found("No resource type defined for path \"%s\"" % pathInfo)
        except (NoSuchObjectException, ParameterException) as exception:
            yield self.not_found(exception.message)
            
class ParameterException(MessageException):
    """Thrown when a URL parameter is invalid or missing"""
    def __init__(self, message):
        self.message = message
        
class MissingParameterException(MessageException):
    """Thrown when a required URL parameter is missing"""
    def __init__(self, name = None):
        self.message = "Missing parameter %s" % name
        
class UnknownViewTypeException(MessageException):
    """Thrown when a view type is invalid"""
    def __init__(self, type):
        self.message = "Unknown view type \"%s\"" % type
        
class View:
    def __init__(self, type, params = {}):
        self.type = type
        self.params = params
        
    def __eq__(self, other):
        print("Is %r equal to %r ? " % (self, other))
        return other != None and self.type == other.type and self.params == other.params
    
    def __repr__(self):
        return "View[%s, %r]" % (self.type, self.params)
    
    def htmlParamsDict(self):
        dict = {}
        if self.type != None:
            dict["view"] = self.type
        for key, value in self.params.items():
            dict["view.%s" % key] = value
        return dict
    
class MethodsByViewType:
    """A dictionary of methods retrieved by view type. 
    Throws UnknownViewTypeException if view type is unknown."""
    def __init__(self):
        self.methods = {}
        
    def __setitem__(self, key, value):
        self.methods[key] = value
    
    def __getitem__(self, key):
        value = self.methods.get(key)
        if value == None:
            raise UnknownViewTypeException(key)
        else:
            return value
        
def byViewMethod(func):
    return MethodsByViewType()

def byView(viewType, methodsByViewType):
    """Decorator for methods to be looked up by view type"""
    def decorator(func):
        methodsByViewType[viewType] = func
        return func
    return decorator
  
class AptrowQueryParams:
    """An object wrapping URL parameters, and presenting them as follows:
    
    Parameters consist of:
    
    * Base parameters passed directly to the resource type in order to retrieve (or create) the base resource.
    * Attribute parameters.
    
    Attribute parameters (and any other special parameters, but there aren't any so far) start with '_'. 
    All base parameters should start with an alphabetic character.
    
    Attribute parameters represent a possible chain of 1 more attribute lookups, each with an attribute
    name and a set of named parameters for each lookup. The lookups are applied first to the base resource, 
    and then in turn to the result of each previous lookup.
    
    The chain of N attribute names is represented by parameters with the key '_<n>' for n = 1 to N. 
    Individual attribute parameters are numbered from 1 up, with the format '_<n>.<name>', where <n> is the 
    number, and <name> is the parameter name (which should also start with an alphabetic character).
    
    The attribute calls are in effect method calls, because they can take parameters. However they are called
    'attributes' to emphasise their read-only nature. """
    
    def __init__(self, htmlParams):
        self.htmlParams = htmlParams
        
    def getString(self, name):
        """Retrieve an optional base resource parameter by name."""
        valuesArray = self.htmlParams.get(name)
        return None if valuesArray == None else valuesArray[0]
    
    def getRequiredString(self, name):
        """Retrieve a required base resource parameter by name."""
        value = self.getString(name)
        if value == None:
            raise ParameterException("Missing parameter %r" % name)
        return value
    
    def attributesAndParams(self):
        """Extract attribute parameters as a list of pairs of names and parameter dicts."""
        count = 1
        finished = False
        while not finished:
            attributeKey = "_%s" % count
            attribute = self.getString(attributeKey)
            if attribute == None:
                finished = True
            else:
                yield (attribute, self.attributeParams(count))
                count += 1
                
    def attributeParams(self, count):
        """For a given attribute lookup (identified by number from 1 up), retrieve parameters
        for that lookup into a dict."""
        params = {}
        for key, value in self.htmlParams.items():
            prefix = "_%s." % count
            if key.startswith(prefix):
                params[key[len(prefix):]] = value[0]
        return params
    
    def getView(self, defaultType = None):
        type = self.getString("view")
        if type == None:
            return None
        else:
            params = {}
            for key, value in self.htmlParams.items():
                if key.startswith("view."):
                    params[key[len("view."):]] = value[0]
            return View(type, params)
    
class NoSuchObjectException(MessageException):
    """Thrown when a Resource has been created and is then later found not to represent a valid resource. 
    Generally thrown by the 'checkExists()' method."""
    def __init__(self, message):
        self.message = message
        
class Param:
    """Parameter definition for an expected base resource parameter."""
    def __init__(self, name, optional = False):
        self.name = name
        self.optional = optional
        
    def getValue(self, stringValue):
        """Get value of parameter from a string value. 
        (Depends on definition of getStringValue method, is a value is supplied.)"""
        if stringValue == None:
            if self.optional:
                return None
            else:
                raise MissingParameterException(self.name)
        else:
            return self.getValueFromString(stringValue)

class StringParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a string value."""
        
    def getValueFromString(self, stringValue):
        """Value for a string parameter is just the string"""
        return stringValue
    
class ResourceParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a URL representing
    another resource (to be used as input when creating the resource being created)."""
        
    def getValueFromString(self, stringValue):
        """Convert to a value by looking up resource from URL"""
        return getResource(stringValue)
    
def getResourceParams(queryParams, paramDefinitions):
    """Get parameters for creating a resource from an AptrowQueryParams and an array of parameter definitions"""
    return [paramDefinition.getValue(queryParams.getString(paramDefinition.name)) 
            for paramDefinition in paramDefinitions]
  
def attribute(*params):
    """Decorator for attribute methods"""
    def decorator(func):
        func.aptrowAttributeParams = params
        return func
    return decorator

class AttributeMethod:
    """An object that replaces a method decorated by @attribute. Wraps the method and parameter definitions."""
    def __init__(self, method, params):
        self.method = method
        self.params = params
        
    def call(self, resource, paramsDict):
        """How to call this method given a resource and a dict of named parameter values."""
        return self.method(resource, *[param.getValue(paramsDict.get(param.name)) for param in self.params])
    
class Resource:
    """Base class for all resources handled and retrieved by the application."""
    def checkExists(self):
        """Default existence check: always passes.
        Resource objects are always created from URL definitions. Often they represent information
        from an external source (such as a file with a specified name), but their initial creation 
        does not depend on such information actually existing or being available (i.e. the file might not exist).
        Override the 'checkExists' method to throw NoSuchObjectException's if a resource is found
        to not represent a valid external resource.
        """
        pass
    
    def defaultView(self):
        return None
    
    def htmlLink(self):
        """Default HTML link for a resource. No styling or any other extras, 
        and uses 'heading()' for display value."""
        return "<a href=\"%s\">%s</a>" % (h(self.url()), h(self.heading()))
    
    
    def attributeUrlParams(self, attribute, count, params):
        """Return URL parameters for a single (numbered) attribute lookup as a map."""
        attributeParams = {"_%s" % count: attribute}
        for key, value in params.items():
            attributeParams["_%s.%s" % (count, key)] = value
        return attributeParams
    
    def page(self, app, view):
        """Return the web page for the resource. Default is to return an HTML page
        by calling the resource's 'html()' method. (Override this method entirely
        if something else is required. Note that currently this application does
        not take any notice of requested content types.)"""
        heading = self.heading()
        response_headers = [('Content-Type','text/html')]
        app.start('200 OK', response_headers)
        yield "<html><head><title>%s</title></head><body>" % h(heading)
        yield app.message
        yield "<h2>%s</h2>" % h(heading)
        try:
            for text in self.html(view): yield text
        except BaseException as error:
            traceback.print_exc()
            yield "<div class =\"aptrowError\">Error: %s</div>" % (h(str(error)),)
        yield "</body></html>"
        
    def resolveAttribute(self, attribute, params):
        """Resolve an attribute, by looking for a method with same name decorated by @attribute decorator."""
        attributeMethod = self.__class__.__dict__.get(attribute)
        if hasattr(attributeMethod, "aptrowAttributeParams"):
            attributeParams = attributeMethod.aptrowAttributeParams
            return attributeMethod(self, *[param.getValue(params.get(param.name)) for param in attributeParams])
        else:
            return None
        
    def viewLink(self, view, description, currentView):
        if view == currentView:
            return description
        else:
            return "<a href=\"%s\">%s</a>" % (self.url(view = view), description)
            
    def viewLinksHtml(self, viewsAndDescriptions, currentView):
        print ("viewsAndDescriptions = %r" % viewsAndDescriptions)
        return " ".join([self.viewLink(view, description, currentView) 
                         for view, description in viewsAndDescriptions])
            
class BaseResource(Resource):
    """Base class for Resource classes representing resources constructed directly 
    from registered resource types."""
    
    def url(self, attributesAndParams = [], view = None):
        """ Construct URL for this resource, from registered resource type and parameter
        values from urlParams(). Any supplied attribute lookups are added to the end of the URL."""
        urlString = "/%s?%s" % (self.__class__.resourcePath, urllib.parse.urlencode(self.urlParams(), True))
        count = 1
        for attribute,params in attributesAndParams:
            urlString += "&%s" % urllib.parse.urlencode(self.attributeUrlParams(attribute, count, params))
            count += 1
        if view != None:
            urlString += "&%s" % urllib.parse.urlencode(view.htmlParamsDict())
        return urlString
    
class AttributeResource(Resource):
    """Base class for Resource classes representing resources which are constructed as attributes
    of other resources. """
    
    def url(self, attributesAndParams = [], view = None):
        """Construct a URL for this resource, by determining the details for the base object and
        the attribute parameters used to look up this object, then append any additional supplied
        attribute lookups before creating the full URL."""
        baseObject, attribute, params = self.baseObjectAndParams()
        return baseObject.url([(attribute, params)] + attributesAndParams, view = view)
        
class FileContents(AttributeResource):
    """A resource representing the contents of a file, to be returned directly
    to the web browser (with an optionally specified content type). The 'file'
    can be any resource which has a suitable 'openBinaryFile()' method."""
    
    def __init__(self, file, contentType = None):
        self.file = file
        self.contentType = contentType
        
    def baseObjectAndParams(self):
        """This resource is assumed to be the 'contents' attribute of the corresponding 'file' resource."""
        return (self.file, "contents", {"contentType": self.contentType})
    
    def checkExists(self):
        """This resource exists if the file resource exists."""
        self.file.checkExists()
    
    def page(self, app, view):
        """Override default page() method to send contents directly with content type (if specified)."""
        response_headers = []
        if self.contentType != None:
            response_headers.append(('Content-Type', self.contentType))
        app.start('200 OK', response_headers)
        with self.file.openBinaryFile() as f:
            yield f.read()
        
@resourceTypeName("dir")
class Directory(BaseResource):
    """A resource representing a directory on the local file system."""

    resourceParams = [StringParam("path")]
    
    def __init__(self, path):
        self.path = os.path.normpath(path)
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"path": [self.path]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Directory: %s" % self.path
    
    def checkExists(self):
        """Check if this directory exists on the local file system (and that it really is a directory)"""
        if not os.path.exists(self.path):
            raise NoSuchObjectException("No such file or directory: %r" % self.path)
        elif not os.path.isdir(self.path):
            raise NoSuchObjectException("Path %r is not a directory" % self.path)
        
    def isDir(self):
        """Yes this resource represents a directory (as opposed to a file)"""
        return True
    
    def fileEntry(self, name):
        """Given the name of an item in the directory, return a resource representing that item."""
        entryPath = os.path.join(self.path, name)
        if os.path.isdir(entryPath):
            return Directory(entryPath)
        else:
            return File(entryPath)
        
    viewsAndDescriptions = [(View(type), type) for type in ["list", "tree"]]
    
    def defaultView(self):
        return View("list")

    def html(self, view):
        """HTML content for directory: show lists of files and sub-directories."""
        yield "<p>Views: %s</p>" % self.viewLinksHtml(Directory.viewsAndDescriptions, 
                                                      view)
        parentDir = self.parent()
        if parentDir:
            yield "<p>Parent: <a href=\"%s\">%s</a></p>" % (parentDir.url(view = view), parentDir.path)
        for text in self.showFilesAndDirectories[view.type](self, view = view): yield text
            
    @attribute()
    def parent(self):
        """Parent directory"""
        parentPath = os.path.dirname(self.path)
        if parentPath == self.path:
            return None
        else:
            return Directory(parentPath)
        
    def getDirAndFileEntries(self):
        entryNames = os.listdir(self.path)
        entries = [(name, self.fileEntry(name)) for name in entryNames]
        dirEntries = [(name, entry) for (name, entry) in entries if entry.isDir()]
        fileEntries = [(name, entry) for (name, entry) in entries if not entry.isDir()]
        return (dirEntries, fileEntries)
    
    @byViewMethod
    def showFilesAndDirectories(self):
        pass
    
    @byView("tree", showFilesAndDirectories)
    def showFilesAndDirectoriesAsTree(self, view = None):
        dirEntries, fileEntries = self.getDirAndFileEntries()
        yield "<ul>"
        for name, entry in fileEntries:
            print (entry.heading())
            yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(), h(name))
        for name, entry in dirEntries:
            print (entry.heading())
            yield "<li><a href = \"%s\">%s</a>" % (entry.url(view = view), h(name))
            for text in entry.showFilesAndDirectoriesAsTree(): yield text
            yield "</li>"
        yield "</ul>"
        
    @byView("list", showFilesAndDirectories)
    def showFilesAndDirectoriesAsList(self, view = None):
        """ Show each of files and sub-directories as a list of links to those resources."""
        dirEntries, fileEntries = self.getDirAndFileEntries()
        if len(dirEntries) > 0:
            yield "<h3>Sub-directories</h3>"
            yield "<ul>"
            for name, entry in dirEntries:
                yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(view = view), h(name))
            yield "</ul>"
        if len(fileEntries) > 0:
            yield "<h3>Files</h3>"
            yield "<ul>"
            for name, entry in fileEntries:
                yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(), h(name))
            yield "</ul>"
    
@resourceTypeName("file")
class File(BaseResource):
    """A resource representing a file on the local file system."""

    resourceParams = [StringParam("path")]

    def __init__(self, path):
        self.path = os.path.normpath(path)
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"path": [self.path]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "File: %s" % self.path
    
    def openBinaryFile(self):
        """Return an open file giving direct access to the contents of the file."""
        return open(self.path, "rb")
        
    def checkExists(self):
        """Check if this file exists on the local file system (and that it really is a file)"""
        if not os.path.exists(self.path):
            raise NoSuchObjectException("No such file or directory: %r" % self.path)
        elif not os.path.isfile(self.path):
            raise NoSuchObjectException("Path %r is not a file" % self.path)
        
    def isDir(self):
        """No this resource is not a directory (because it's a file)"""
        return False
    
    @attribute()
    def dir(self):
        """Directory containing file"""
        return Directory(os.path.dirname(self.path))

    def html(self, view):
        """HTML content for file: show various details, including links to contents
        and to alternative views of the file."""
        fileSize = os.path.getsize(self.path)
        yield "<p>Information about file <b>%s</b>: %s bytes</p>" % (h(self.path), fileSize)
        directory = self.dir()
        yield "<p>Containing directory: <a href=\"%s\">%s</a></p>" % (directory.url(), h(directory.path))
        yield "<p><a href =\"%s\">contents</a>" % FileContents(self).url()
        yield " (<a href =\"%s\">text</a>)" % FileContents(self, "text/plain").url()
        yield " (<a href =\"%s\">html</a>)" % FileContents(self, "text/html").url()
        yield "</p>"
        # Link showing file as a zip file (you'll find out when you click on it if it really is a Zip file).
        yield "<p><a href =\"%s\">zipFile</a> " % ZipFile(self).url() 
        
    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType):
        """Return contents of file with optional content type"""
        return FileContents(self, contentType)
        
@resourceTypeName("string")
class String(BaseResource):
    """A resource representing a String value. (There is no external resource, as the 
    string is provided as a parameter. This resource type is mostly useful for testing, 
    for example to test HTML quoting. But it could have other uses, for example to display
    all the properties of a string, what characters it contains, how long it is, etc.)"""
    
    resourceParams = [StringParam("value")]

    def __init__(self, value):
        self.value = value
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"value": [self.value]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "String: %r" % self.value
    
    def html(self, view):
        """HTML content for string: show it in bold."""
        yield "<p>String: <b>%s</b></p>" % h(self.value)
        
import zipfile

class ZipItemsTree:
    """Representation of items in a zip file as a recursively defined tree structure"""
    def __init__(self):
        self.files = []
        self.subdirs = {}
        
    def addPath(self, path, zipItem):
        slashPos = path.find("/")
        if slashPos == -1:
            self.files.append((path, zipItem))
        else:
            subdir = path[:slashPos]
            restOfPath = path[slashPos+1:]
            subdirTree = self.subdirs.get(subdir)
            if subdirTree == None:
                subdirTree = ZipItemsTree()
                self.subdirs[subdir] = subdirTree
            if len(restOfPath) > 0:
                subdirTree.addPath(restOfPath, zipItem)
    
    def asHtml(self):
        buffer = io.StringIO()
        subdirKeys = self.subdirs.keys()
        if len(subdirKeys) + len(self.files) > 0:
            buffer.write("<ul>")
            for file,zipItem in self.files:
                buffer.write("<li><a href=\"%s\">%s</a> <small>(<a href=\"%s\">contents</a>)</small></li>" 
                             % (zipItem.url(), h(file), zipItem.contents().url()))
            for subdir in subdirKeys:
                 buffer.write("<li>%s\n" % h(subdir))
                 buffer.write("%s\n" % self.subdirs[subdir].asHtml())
                 buffer.write("</li>\n")
            buffer.write("</ul>")
        return buffer.getvalue()
        
@resourceTypeName("zipfile")
class ZipFile(BaseResource):
    """A resource representing a Zip file, which gives access to the items within the Zip file
    as nested resources. The ZipFile resource needs to be created from a 'file' resource, where
    the 'file' can be anything with a suitable 'openBinaryFile()' method."""
    
    resourceParams = [ResourceParam("file")]

    def __init__(self, fileResource):
        self.fileResource = fileResource
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"file": [self.fileResource.url()]}
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Zip file[%s]" % self.fileResource.heading()
    
    def checkExists(self):
        self.fileResource.checkExists()

    def openZipFile(self):
        """Return on open (read-only) zipfile.ZipFile object."""
        return zipfile.ZipFile(self.fileResource.openBinaryFile(), "r")
    
    def getZipInfos(self):
        """Get the list of ZipInfo objects representing information about the
        items in the zip file."""
        zipFile = self.openZipFile()
        try:
            return zipFile.infolist()
        finally:
            zipFile.close()
            
    viewsAndDescriptions = [(View(type), type) for type in ["list", "tree"]]
            
    def defaultView(self):
        return View("list")

    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield "<p>Resource <b>%s</b> interpreted as a Zip file</p>" % self.fileResource.htmlLink()
        yield "<p>Views: %s</p>" % self.viewLinksHtml(ZipFile.viewsAndDescriptions, view)
        for text in self.showZipItems[view.type](self): yield text
            
    @byViewMethod
    def showZipItems(self):
        pass

    @byView("list", showZipItems)
    def showZipItemsAsList(self):
        """Show list of links to zip items within the zip file."""
        zipInfos = self.getZipInfos()
        yield "<h3>Items</h3>"
        yield "<ul>"
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            yield "<li><a href=\"%s\">%s</a></li>" % (ZipItem(self, itemName).url(), h(itemName))
        yield "</ul>"
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self):
        """Show list of links to zip items as a tree."""
        zipInfos = self.getZipInfos()
        yield "<h3>Items Tree</h3>"
        zipItemsTree = ZipItemsTree()
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            zipItemsTree.addPath(itemName, ZipItem(self, itemName))
        yield zipItemsTree.asHtml()
        
    @attribute(StringParam("name"))
    def item(self, name):
        """Return a named item from this zip file as a ZipItem resource"""
        return ZipItem(self, name)
    
    @attribute(StringParam("path"))
    def dir(self, path):
        """Return a named item from this zip file as a ZipFileDir resource"""
        return ZipFileDir(self, path)
    
class ZipFileDir(AttributeResource):
    """A resource representing a directory within a zip file. Considered to exist if the path
    name ends in '/', and, either (1) a corresponding Zip item exists, or (2) other Zip items exist 
    with the path as a prefix. The root directory is represented by '/', even though for matching
    purposes, it is really ''."""
    
    def __init__(self, zipFile, path):
        self.zipFile = zipFile
        self.path = path
        self.matchPath = "" if path == "/" else path
        
    def isRoot(self):
        return self.path == "/"
    
    def baseObjectAndParams(self):
        """This resource is defined as a named 'dir' attribute of the enclosing ZipFile resource."""
        return (self.zipFile, "dir", {"path": self.path})
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Directory %s in %s" % (self.path, self.zipFile.heading())
    
    def checkExists(self):
        self.zipFile.checkExists()
        if not (self.isRoot() or self.path.endswith("/")):
            raise NoSuchObjectException("Invalid Zip dir %s does not end with '/'" % self.path)
        zipFile = self.zipFile.openZipFile()
        try:
            zipInfo = zipFile.getinfo(self.path)
        except KeyError:
            childItems = self.getChildItems()
            if len(childItems) == 0:
                raise NoSuchObjectException("No item or child items for zip dir %s in %s" 
                                            % (self.path, self.zipFile.heading()))
        
    def defaultView(self):
        return View("list")

    @attribute()
    def parent(self):
        """Parent directory"""
        if self.isRoot():
            return None
        else:
            previousSlashPos = self.path[:-1].rfind("/")
            if previousSlashPos == -1:
                return ZipFileDir(self.zipFile, "/")
            else:
                return ZipFileDir(self.zipFile, self.path[0:previousSlashPos+1])
            
    def getZipInfos(self):
        return [zipInfo for zipInfo in self.zipFile.getZipInfos() if zipInfo.filename.startswith(self.matchPath)]
        
    def getChildItems(self):
        return [ZipItem(self.zipFile, zipInfo.filename) for zipInfo in self.getZipInfos()]
    
    @attribute(StringParam("name"))
    def item(self, name):
        """Return a named item from this ZipFileDir as a ZipItem resource"""
        return ZipItem(self.zipFile, self.path + name)
    
    viewsAndDescriptions = [(View(type), type) for type in ["list", "tree"]]
    
    @byViewMethod
    def showZipItems(self):
        pass

    @byView("list", showZipItems)
    def showZipItemsAsList(self, view = None):
        """Show list of links to zip items within the zip file."""
        yield "<h3>Items</h3>"
        yield "<ul>"
        for childItem in self.getChildItems():
            yield "<li><a href=\"%s\">%s</a></li>" % (childItem.url(), h(childItem.name))
        yield "</ul>"
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self, view = None):
        yield "<h3>Items (Tree)</h3>"
        yield "<ul>"
        zipItemsTree = ZipItemsTree()
        pathLength = len(self.path)
        for zipInfo in self.getZipInfos():
            itemName = zipInfo.filename[pathLength:]
            if itemName != "":
                zipItemsTree.addPath(itemName, ZipItem(self, itemName))
        yield zipItemsTree.asHtml()
        yield "</ul>"
        
        
    def html(self, view):
        """HTML content for this resource."""
        yield "<p>Views: %s</p>" % self.viewLinksHtml(ZipFileDir.viewsAndDescriptions, 
                                                      view)
        yield "<p>Zip file: <a href=\"%s\">%s</a></p>" % (self.zipFile.url(), self.zipFile.heading())
        parentDir = self.parent()
        if parentDir:
            parentPath = parentDir.path
            yield "<p>Parent: <a href=\"%s\">%s</a></p>" % (parentDir.url(), parentPath)
        for text in self.showZipItems[view.type](self): yield text
        
class ZipItem(AttributeResource):
    """A resource representing a named item within a zip file. (Note: current implementation
    specifies name only, so if there are multiple items with the same name -- something generally
    to be avoided when creating zip files, but it can happen -- there is currently no way to access 
    them. Some additional information would have to be included in this resource class to handle multiple items.)"""
    def __init__(self, zipFile, name):
        self.zipFile = zipFile
        self.name = name
        
    def baseObjectAndParams(self):
        """This resource is defined as a named 'item' attribute of the enclosing ZipFile resource."""
        return (self.zipFile, "item", {"name": self.name})
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Item %s in %s" % (self.name, self.zipFile.heading())
    
    def getZipInfo(self):
        return self.zipFile.openZipFile().getinfo(self.name)
    
    def checkExists(self):
        self.zipFile.checkExists()
        zipFile = self.zipFile.openZipFile()
        try:
            zipInfo = zipFile.getinfo(self.name)
        except KeyError:
            raise NoSuchObjectException("Zip item %r not found in %s" % (self.name, self.zipFile.heading()))

    def openBinaryFile(self):
        """Return an open file giving direct access to the contents of the zip item.
        io.BytesIO is currently used as an intermediary, because the 'file-like' features
        of the object returned by ZipFile.open are somewhat limited.
        """
        print("ZipItem.openBinaryFile for name %s ..." % self.name)
        zipFile = self.zipFile.openZipFile()
        memoryFile = io.BytesIO()
        zipItem = zipFile.open(self.name, "r")
        zipItemBytes = zipItem.read()
        print (" read %s bytes" % len(zipItemBytes))
        memoryFile.write(zipItemBytes)
        memoryFile.seek(0)
        zipItem.close()
        zipFile.close()
        return memoryFile
    
    zipInfoAttributes = "filename date_time compress_type comment extra create_system create_version extract_version reserved flag_bits volume internal_attr external_attr header_offset CRC compress_size file_size".split()
    
    def zipInfoHtml(self):
        zipInfo = self.getZipInfo()
        buffer = io.StringIO()
        buffer.write("<h3>Zip Info attributes</h3>")
        buffer.write("<table>\n")
        for attr in ZipItem.zipInfoAttributes:
            buffer.write("<tr><td>%s:</td><td><b>%r</b></td>\n" % (attr, getattr(zipInfo, attr)))
        buffer.write("</table>\n")
        return buffer.getvalue()
    
    def asZipFileDir(self):
        return ZipFileDir(self.zipFile, self.name)
    
    def html(self, view):
        """HTML content for zip item. Somewhat similar to what is displayed for File resource."""
        yield "<p><a href=\"%s\">Content</a>" % FileContents(self, "text/plain").url()
        yield " (<a href =\"%s\">html</a>)" % FileContents(self, "text/html").url()
        yield "</p>"
        yield "<p><a href =\"%s\">zipFile</a> " % ZipFile(self).url()
        if self.name.endswith("/"):
            zipFileDir = self.asZipFileDir()
            yield "<p><a href =\"%s\">(as Zip directory)</a> " % zipFileDir.url()
        yield self.zipInfoHtml()

    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType = None):
        """Return contents of zip item with optional content type"""
        return FileContents(self, contentType)

# Run the application as a web server on localhost:8000 (preventing external IP access)
# SECURITY NOTE: This demo application gives read-only access to all files and directories
# on the local filesystem which can be accessed by the user running the application. So beware.
        
from wsgiref.simple_server import make_server

httpd = make_server('localhost', 8000, AptrowApp)
print("Serving HTTP on port 8000...")

# Respond to requests until process is killed
httpd.serve_forever()

# suggested starting URL: http://localhost:8000/dir?path=c:\
