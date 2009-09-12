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
class Directory(Resource):
    """A resource representing a directory on the local file system."""

    resourceParams = [StringParam("path")]
    
    def init(self, path):
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
    
    def fileSearchForm(self):
        action, params, count = self.formActionParamsAndCount()
        count += 1
        return tag.formWithParams(action, params, 
                                  "Search for file: ", 
                                  tag.INPUT(name = "_%s" % count, value = "search", type = "hidden"), 
                                  tag.INPUT(name = "_%s.pattern" % count, 
                                            type = "text", length = 30), tag.NBSP, 
                                  tag.INPUT(type = "submit", value = "Search"))
    
    def html(self, view):
        """HTML content for directory: show lists of files and sub-directories."""
        yield tag.P("Views ", *self.listAndTreeViewLinks(view))
        parentDir = self.parent()
        if parentDir:
            yield tag.P("Parent: ", tag.A(h(parentDir.path), href = parentDir.url(view = view)))
        yield self.fileSearchForm()
        for text in self.showFilesAndDirectories[view.type](self, view): yield text
            
    @attribute()
    def parent(self):
        """Parent directory"""
        parentPath = os.path.dirname(self.path)
        if parentPath == self.path:
            return None
        else:
            return Directory(parentPath)
        
    @attribute(StringParam("pattern"))
    def search(self, pattern):
        """Search for a file containing pattern in name."""
        return SearchForFileInDirectory(self, pattern)
        
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
        yield tag.UL().start()
        for name, entry in fileEntries:
            print (entry.heading())
            yield tag.LI(tag.A(h(name), href = entry.url()))
        for name, entry in dirEntries:
            print (entry.heading())
            yield tag.LI().start()
            yield tag.A(h(name), href = entry.url(view = view))
            if depth == None or depth > 1:
                for element in entry.showFilesAndDirectoriesAsTree(view, view.depthLessOne()): 
                    yield element
            else:
                yield " ..."
            yield tag.LI().end()
        yield tag.UL().end()
        
    @byView("list", showFilesAndDirectories)
    def showFilesAndDirectoriesAsList(self, view):
        """ Show each of files and sub-directories as a list of links to those resources."""
        dirEntries, fileEntries = self.getDirAndFileEntries()
        if len(dirEntries) > 0:
            yield tag.H3("Sub-directories")
            yield tag.UL().start()
            for name, entry in dirEntries:
                yield tag.LI(tag.A(h(name), href = entry.url(view = view)))
            yield tag.UL().end()
        if len(fileEntries) > 0:
            yield tag.H3("Files")
            yield tag.UL().start()
            for name, entry in fileEntries:
                yield tag.LI(tag.A(h(name), href = entry.url()))
            yield tag.UL().end()
    
@resourceTypeNameInModule("file", aptrowModule)
class File(Resource):
    """A resource representing a file on the local file system."""

    resourceParams = [StringParam("path")]
    
    resourceInterfaces = [fileLikeResource]

    def init(self, path):
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
        yield tag.P("Information about file ", tag.B(h(self.path)), ": ", fileSize, " bytes")
        directory = self.dir()
        yield tag.P("Containing directory: ", tag.A(h(directory.path), href = directory.url()))
        yield tag.P(tag.A("contents", href = FileContents(self).url()), 
                    " (", tag.A("text", href = FileContents(self, "text/plain").url()), ")", 
                    " (", tag.A("html", href = FileContents(self, "text/html").url()), ")")
        
    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType):
        """Return contents of file with optional content type"""
        return FileContents(self, contentType)
        
@resourceTypeNameInModule("searchForFile", aptrowModule)
class SearchForFileInDirectory(Resource):

    resourceParams = [ResourceParam("dir"), StringParam("pattern")]

    def init(self, directory, pattern):
        self.directory = directory
        self.pattern = pattern
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"dir": [self.directory.url()], "pattern": [self.pattern]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Search for %r in %s" % (self.pattern, self.directory.heading())
    
    def checkExists(self):
        self.directory.checkExists()
        
    def filesContainingPattern(self, directory, relativePath = None):
        dirEntries, fileEntries = directory.getDirAndFileEntries()
        for name, fileResource in fileEntries:
            if name.find(self.pattern) != -1:
                fileRelativePath = name if relativePath == None else os.path.join(relativePath, name)
                yield fileResource, fileRelativePath
        for name, dirResource in dirEntries:
            dirRelativePath = name if relativePath == None else os.path.join(relativePath, name)
            if name.find(self.pattern) != -1:
                yield dirResource, dirRelativePath
            for resourceAndPath in self.filesContainingPattern(dirResource, dirRelativePath):
                yield resourceAndPath
    
    def html(self, view):
        """Show results of search for a file containing a pattern in the directory"""
        yield tag.P(tag.A("Directory", href = self.directory.url()))
        yield tag.P ("Results of search ...")
        yield tag.UL().start()
        for resource, relativePath in self.filesContainingPattern(self.directory):
            yield tag.LI(tag.A(h(relativePath), href = resource.url()))
        yield tag.UL().end()
