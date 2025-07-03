from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import JSONField
import os
from .storage import PreserveFilenameStorage

# Add this function to handle file uploads with original filenames
def user_directory_path(instance, filename):
    # Get the username
    username = instance.user.username
    # Return the path: uploads/username/original_filename
    return os.path.join('uploads', username, filename)

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, role='user'):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user
 
    def create_superuser(self, username, password):
        user = self.create_user(username, password, role='admin')
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user
 
class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'))
    username = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    can_delete_files = models.BooleanField(default=False)  # Permission to delete files
 
    USERNAME_FIELD = 'username'
 
    objects = UserManager()
 
    def __str__(self):
        return self.username
    

class FileUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=user_directory_path, storage=PreserveFilenameStorage())
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Comparison(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    file1 = models.ForeignKey(FileUpload, related_name='file1_comparisons', on_delete=models.CASCADE)
    file2 = models.ForeignKey(FileUpload, related_name='file2_comparisons', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    range1= models.CharField(max_length=255, blank=True, null=True)
    range2= models.CharField(max_length=255, blank=True, null=True)
    column1 = models.CharField(max_length=255, blank=True, null=True)
    column2 = models.CharField(max_length=255, blank=True, null=True)
    results = JSONField()

    def __str__(self):
        return f"Comparison {self.id} between {self.file1.file_name} and {self.file2.file_name}"
    

class Database_Connection(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='database_connections')
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    DSN = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Connection {self.id} by {self.user.username}"


class Database_Comparison(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='database_comparisons')
    connection1 = models.ForeignKey(Database_Connection, related_name='source_comparisons', on_delete=models.CASCADE)
    connection2 = models.ForeignKey(Database_Connection, related_name='target_comparisons', on_delete=models.CASCADE)
    schema1 = models.CharField(max_length=255)
    schema2 = models.CharField(max_length=255)
    table1 = models.CharField(max_length=255)
    table2 = models.CharField(max_length=255)
    primary_key1 = models.CharField(max_length=255)
    primary_key2 = models.CharField(max_length=255)
    results = JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DB Comparison {self.id} between {self.schema1}.{self.table1} and {self.schema2}.{self.table2}"




