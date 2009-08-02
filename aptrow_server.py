import aptrow
from aptrow import addModule, runAptrowServer

# define resource modules
addModule ("files",   "files_module")
addModule ("strings", "strings_module")
addModule ("zip",     "zip_module")
addModule ("aptrow",  "aptrow_module")

# Run the application as a web server on localhost:8000 (preventing external IP access)
# SECURITY NOTE: This demo application gives read-only access to all files and directories
# on the local filesystem which can be accessed by the user running the application. So beware.
        
runAptrowServer('localhost', 8000)

# suggested starting URL: http://localhost:8000/files/dir?path=c:\
