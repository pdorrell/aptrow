""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

import urllib
import os
import traceback
import cgi
import io

def h(value):
    return cgi.escape(value)

def hr(value):
    return h(value.__repr__())

resourceClasses = {}

def resourceTypeName(name):
    def registerResourceClass(resourceClass):
        print("Registering resource class %s as %r" % (resourceClass.__name__, name))
        resourceClasses[name] = resourceClass
        resourceClass.resourcePath = name
        return resourceClass
    return registerResourceClass

class ResourceTypeNoFoundForPathException(Exception):
    def __init__(self, path):
        self.path = path
        self.message = "No resource type defined for path \"%s\"" % path

def getResource(url):
    if url.startswith("/"):
        localUrl = url[1:]
        queryStart = localUrl.find("?")
        if queryStart == -1:
            path = localUrl
            query = None
        else:
            path = localUrl[:queryStart]
            query = localUrl[queryStart+1:]
        return getResourceFromPathAndQuery(path, query)
    else:
        raise Error("Non-local resource URL's not yet implemented (doesn't start with '/'): %s" % localUrl)
    
def getResourceFromPathAndQuery(path, query):
    queryParams = urllib.parse.parse_qs(query)
    resourceClass = resourceClasses.get(path)
    if resourceClass == None:
        raise ResourceTypeNoFoundForPathException(path)
    aptrowQueryParams = AptrowQueryParams(queryParams)
    object = resourceClass(*getResourceParams(aptrowQueryParams, resourceClass.resourceParams))
    for attribute,params in aptrowQueryParams.attributesAndParams():
        object = object.resolveAttribute(attribute, params)
        if object == None:
            raise Error("Failed to resolve attribute %s" % attribute)
    return object
                    
class AptrowApp:
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start = start_response
        #print ("environ = %r" % environ)
        
    def not_found(self, message):
        self.start('404 Not Found', [('Content-type', 'text/plain')])
        return message
    
    def __iter__(self):
        pathInfo = self.environ['PATH_INFO']
        print ("pathInfo = %r" % pathInfo)
        if pathInfo.startswith("/"):
            pathInfo = pathInfo[1:]
        queryString = self.environ['QUERY_STRING']
        print ("queryString = %r" % queryString)
        try:
            object = getResourceFromPathAndQuery(pathInfo, queryString)
            object.checkExists()
            msg = "<p>AppClass sez, you requested <strong>%s</strong> with query string <b>%s</b></p>"
            self.message = msg % (h(pathInfo), hr(queryString))
            for text in object.page(self): yield text
        except ResourceTypeNoFoundForPathException as exc:
            yield self.not_found("No resource type defined for path \"%s\"" % pathInfo)
        except (NoSuchObjectException, ParameterException) as exception:
            yield self.not_found(exception.message)
            
class ParameterException(Exception):
    def __init__(self, message):
        self.message = message
  
class AptrowQueryParams:
    def __init__(self, htmlParams):
        self.htmlParams = htmlParams
        self.attributes = self.htmlParams.get("_attribute")
        
    def getString(self, name):
        valuesArray = self.htmlParams.get(name)
        return None if valuesArray == None else valuesArray[0]
    
    def getRequiredString(self, name):
        value = self.getString(name)
        if value == None:
            raise ParameterException("Missing parameter %r" % name)
        return value
    
    def attributesAndParams(self):
        if self.attributes != None:
            count = 1
            for attribute in self.attributes:
                yield (attribute, self.attributeParams(count))
                count += 1
                
    def attributeParams(self, count):
        params = {}
        for key, value in self.htmlParams.items():
            prefix = "_%s." % count
            if key.startswith(prefix):
                params[key[len(prefix):]] = value[0]
        return params
    
class NoSuchObjectException(Exception):
    def __init__(self, message):
        self.message = message
        
class StringParam:
    def __init__(self, name):
        self.name = name
        
    def getValue(self, queryParams):
        return queryParams.getRequiredString(self.name)
    
class ResourceParam:
    def __init__(self, name):
        self.name = name
        
    def getValue(self, queryParams):
        return getResource(queryParams.getRequiredString(self.name))
    
def getResourceParams(queryParams, paramDefinitions):
    return [paramDefinition.getValue(queryParams) for paramDefinition in paramDefinitions]
  
class Resource:
    def checkExists(self):
        pass
    
    def htmlLink(self):
        return "<a href=\"%s\">%s</a>" % (h(self.url()), h(self.heading()))
    
    def attributeUrlParams(self, attribute, count, params):
        attributeParams = {"_attribute": attribute}
        for key, value in params.items():
            attributeParams["_%s.%s" % (count, key)] = value
        return attributeParams
    
    def page(self, app):
        heading = self.heading()
        response_headers = [('Content-Type','text/html')]
        app.start('200 OK', response_headers)
        yield "<html><head><title>%s</title></head><body>" % h(heading)
        yield app.message
        yield "<h2>%s</h2>" % h(heading)
        try:
            for text in self.html(): yield text
        except BaseException as error:
            traceback.print_exc()
            yield "<div class =\"aptrowError\">Error: %s</div>" % (hr(error.args),)
        yield "</body></html>"
        
class BaseResource(Resource):
    def url(self, attributesAndParams = []):
        urlString = "/%s?%s" % (self.__class__.resourcePath, urllib.parse.urlencode(self.urlParams(), True))
        count = 1
        for attribute,params in attributesAndParams:
            urlString += "&%s" % urllib.parse.urlencode(self.attributeUrlParams(attribute, count, params))
            count += 1
        return urlString
    
class AttributeResource(Resource):
    def url(self, attributesAndParams = []):
        baseObject, attribute, params = self.baseObjectAndParams()
        return baseObject.url([(attribute, params)] + attributesAndParams)
        return self.urlFromBaseObject(attributesAndParams)
        
class FileContents(AttributeResource):
    def __init__(self, file, contentType = None):
        self.file = file
        self.contentType = contentType
        
    def baseObjectAndParams(self):
        return (self.file, "contents", {"contentType": self.contentType})
    
    def checkExists(self):
        self.file.checkExists()
    
    def page(self, app):
        response_headers = []
        if self.contentType != None:
            response_headers.append(('Content-Type', self.contentType))
        app.start('200 OK', response_headers)
        with self.file.openBinaryFile() as f:
            yield f.read()
        
@resourceTypeName("dir")
class Directory(BaseResource):
    resourceParams = [StringParam("path")]
    
    def __init__(self, path):
        self.path = path
        
    def urlParams(self):
        return {"path": [self.path]}

    def heading(self):
        return "Directory: %r" % self.path
    
    def checkExists(self):
        if not os.path.exists(self.path):
            raise NoSuchObjectException("No such file or directory: %r" % self.path)
        elif not os.path.isdir(self.path):
            raise NoSuchObjectException("Path %r is not a directory" % self.path)
        
    def isDir(self):
        return True
    
    def fileEntry(self, name):
        entryPath = os.path.join(self.path, name)
        if os.path.isdir(entryPath):
            return Directory(entryPath)
        else:
            return File(entryPath)
    
    def html(self):
        for text in self.listFilesAndDirectoriesInHtml(): yield text
        
    def listFilesAndDirectoriesInHtml(self):
        path = self.path
        entryNames = os.listdir(path)
        entries = [(name, self.fileEntry(name)) for name in entryNames]
        dirEntries = [(name, entry) for (name, entry) in entries if entry.isDir()]
        fileEntries = [(name, entry) for (name, entry) in entries if not entry.isDir()]
        if len(dirEntries) > 0:
            yield "<h3>Sub-directories</h3>"
            yield "<ul>"
            for name, entry in dirEntries:
                yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(), h(name))
            yield "</ul>"
        if len(fileEntries) > 0:
            yield "<h3>Files</h3>"
            yield "<ul>"
            for name, entry in fileEntries:
                yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(), h(name))
            yield "</ul>"
        
@resourceTypeName("file")
class File(BaseResource):
    resourceParams = [StringParam("path")]

    def __init__(self, path):
        self.path = path
        
    def urlParams(self):
        return {"path": [self.path]}

    def heading(self):
        return "File: %r" % self.path
    
    def openBinaryFile(self):
        return open(self.path, "rb")
        
    def checkExists(self):
        if not os.path.exists(self.path):
            raise NoSuchObjectException("No such file or directory: %r" % self.path)
        elif not os.path.isfile(self.path):
            raise NoSuchObjectException("Path %r is not a file" % self.path)
        
    def isDir(self):
        return False
    
    def html(self):
        fileSize = os.path.getsize(self.path)
        yield "<p>Information about file <b>%s</b>: %s bytes</p>" % (h(self.path), fileSize)
        yield "<p><a href =\"%s\">contents</a>" % FileContents(self).url()
        yield " (<a href =\"%s\">text</a>)" % FileContents(self, "text/plain").url()
        yield " (<a href =\"%s\">html</a>)" % FileContents(self, "text/html").url()
        yield "</p>"
        yield "<p><a href =\"%s\">zipFile</a> " % ZipFile(self).url()
        
    def resolveAttribute(self, attribute, params):
        if attribute == "contents":
            return FileContents(self, params.get("contentType"))
        else:
            return None
        
@resourceTypeName("string")
class String(BaseResource):
    resourceParams = [StringParam("value")]

    def __init__(self, value):
        self.value = value
        
    def urlParams(self):
        return {"value": [self.value]}

    def heading(self):
        return "String: %r" % self.value
    
    def html(self):
        yield "<p>String: <b>%s</b></p>" % h(self.value)
        
import zipfile
        
@resourceTypeName("zipfile")
class ZipFile(BaseResource):
    resourceParams = [ResourceParam("file")]

    def __init__(self, fileResource):
        self.fileResource = fileResource
        
    def urlParams(self):
        return {"file": [self.fileResource.url()]}
        
    def heading(self):
        return "Zip file[%s]" % self.fileResource.heading()
    
    def openZipFile(self):
        return zipfile.ZipFile(self.fileResource.openBinaryFile(), "r")
    
    def getZipInfos(self):
        zipFile = self.openZipFile()
        try:
            return zipFile.infolist()
        finally:
            zipFile.close()
            
    def html(self):
        yield "<p>Resource <b>%s</b> interpreted as a Zip file</p>" % self.fileResource.htmlLink()
        for text in self.listZipInfosInHtml(): yield text

    def listZipInfosInHtml(self):
        zipInfos = self.getZipInfos()
        yield "<h3>Items</h3>"
        yield "<ul>"
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            yield "<li><a href=\"%s\">%s</a></li>" % (ZipItem(self, itemName).url(), h(itemName))
        yield "</ul>"
        
    def resolveAttribute(self, attribute, params):
        if attribute == "item":
            return ZipItem(self, params.get("name"))
        else:
            return None
        
class ZipItem(AttributeResource):
    def __init__(self, zipFile, name):
        self.zipFile = zipFile
        self.name = name
        
    def baseObjectAndParams(self):
        return (self.zipFile, "item", {"name": self.name})
    
    def heading(self):
        return "Item %s in %s" % (self.name, self.zipFile.heading())
    
    def openBinaryFile(self):
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
    
    def html(self):
        yield "<p><a href=\"%s\">Content</a>" % FileContents(self, "text/plain").url()
        yield " (<a href =\"%s\">html</a>)" % FileContents(self, "text/html").url()
        yield "</p>"
        yield "<p><a href =\"%s\">zipFile</a> " % ZipFile(self).url()

    def resolveAttribute(self, attribute, params):
        if attribute == "contents":
            return FileContents(self, params.get("contentType"))
        else:
            return None

from wsgiref.simple_server import make_server

httpd = make_server('localhost', 8000, AptrowApp)
print("Serving HTTP on port 8000...")

# Respond to requests until process is killed
httpd.serve_forever()

# suggested starting URL: http://localhost:8000/dir?path=c:\
