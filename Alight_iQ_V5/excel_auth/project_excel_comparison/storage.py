from django.core.files.storage import FileSystemStorage
import os

class PreserveFilenameStorage(FileSystemStorage):
    def get_valid_name(self, name):
        """Return the given name without any modifications."""
        return name
        
    def get_available_name(self, name, max_length=None):
        """If a file with the same name already exists, add a number to the end."""
        if self.exists(name):
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)
            
            # Add a number to the filename
            counter = 1
            while self.exists(name):
                name = os.path.join(dir_name, f"{file_root}_{counter}{file_ext}")
                counter += 1
                
        return name
