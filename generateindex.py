"""Generates an index.html file for the repository."""

import docutils.core 

if __name__ == "__main__":
    docutils.core.publish_file(source_path ="README.rst", destination_path ="index.html", writer_name ="html") 
