""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

from aptrow import *

# Aptrow module giving access to files and directories in the local file system

aptrowModule = ResourceModule()
        
@resourceTypeNameInModule("dir", aptrowModule)
class Directory(BaseResource):
    """A resource representing a directory on the local file system."""

    resourceParams = [StringParam("path")]
    
    def __init__(self, path):
        BaseResource.__init__(self)
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
        
    def defaultView(self):
        return View("list")
    
    def html(self, view):
        """HTML content for directory: show lists of files and sub-directories."""
        yield "<p>Views: %s</p>" % self.listAndTreeViewLinks(view)
        parentDir = self.parent()
        if parentDir:
            yield "<p>Parent: <a href=\"%s\">%s</a></p>" % (parentDir.url(view = view), parentDir.path)
        for text in self.showFilesAndDirectories[view.type](self, view): yield text
            
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
    def showFilesAndDirectoriesAsTree(self, view, depth = None):
        if depth == None:
            depth = view.depth
        dirEntries, fileEntries = self.getDirAndFileEntries()
        yield "<ul>"
        for name, entry in fileEntries:
            print (entry.heading())
            yield "<li><a href = \"%s\">%s</a></li>" % (entry.url(), h(name))
        for name, entry in dirEntries:
            print (entry.heading())
            yield "<li><a href = \"%s\">%s</a>" % (entry.url(view = view), h(name))
            if depth == None or depth > 1:
                for text in entry.showFilesAndDirectoriesAsTree(view, view.depthLessOne()): 
                    yield text
            else:
                yield " ..."
            yield "</li>"
        yield "</ul>"
        
    @byView("list", showFilesAndDirectories)
    def showFilesAndDirectoriesAsList(self, view):
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
    
@resourceTypeNameInModule("file", aptrowModule)
class File(BaseResource):
    """A resource representing a file on the local file system."""

    resourceParams = [StringParam("path")]
    
    resourceInterfaces = [fileLikeResource]

    def __init__(self, path):
        BaseResource.__init__(self)
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
        
    def extension(self):
        lastDotPos = self.path.rfind(".")
        if lastDotPos == -1:
            return ""
        else:
            return self.path[lastDotPos+1:]
        
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
        
    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType):
        """Return contents of file with optional content type"""
        return FileContents(self, contentType)
        
