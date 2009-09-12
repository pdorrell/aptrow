""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

import aptrow
from aptrow import addModule, runAptrowServer

# define resource modules
# format: addModule (<prefix>, <python module>)

addModule ("base",    "aptrow")
addModule ("files",   "files_module")
addModule ("strings", "strings_module")
addModule ("zip",     "zip_module")
addModule ("aptrow",  "aptrow_module")
addModule ("sqlite",  "sqlite_module")

# Run the application as a web server on localhost:8000 (preventing external IP access)
# SECURITY NOTE: This demo application gives read-only access to all files and directories
# on the local filesystem which can be accessed by the user running the application. So beware.
#
# (Also, this application may create temporary files which it does not delete, which are copies
#  of the contents of 'file-like' objects which are not themselves files.)
        
runAptrowServer('localhost', 8000)

# suggested starting URL: http://localhost:8000/files/dir?path=c:\
