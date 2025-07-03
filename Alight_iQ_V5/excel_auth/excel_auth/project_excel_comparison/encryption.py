import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
import tempfile

# Get the encryption key from settings, or generate one if not available
def get_encryption_key():
    key = getattr(settings, 'FILE_ENCRYPTION_KEY', None)
    if not key:
        # If no key is set, use the secret key to derive one
        # Note: In production, you should use a separate strong key
        salt = b'excel_comparison_salt'  # You should change this in production
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key

def encrypt_file(file_path):
    """
    Encrypt a file and replace it with the encrypted version
    
    Args:
        file_path: Path to the file to encrypt
    
    Returns:
        Path to the encrypted file (same as input)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")
    
    # Get the key
    key = get_encryption_key()
    fernet = Fernet(key)
    
    # Read the file
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    # Encrypt the data
    encrypted_data = fernet.encrypt(file_data)
    
    # Write the encrypted data back to the file
    with open(file_path, 'wb') as file:
        file.write(encrypted_data)
    
    return file_path

def decrypt_file(encrypted_file_path):
    """
    Decrypt a file and return a path to a temporary decrypted version
    
    Args:
        encrypted_file_path: Path to the encrypted file
        
    Returns:
        Path to the temporary decrypted file
    """
    if not os.path.exists(encrypted_file_path):
        raise FileNotFoundError(f"File {encrypted_file_path} not found")
    
    # Get the key
    key = get_encryption_key()
    fernet = Fernet(key)
    
    # Read the encrypted file
    with open(encrypted_file_path, 'rb') as file:
        encrypted_data = file.read()
    
    # Decrypt the data
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception as e:
        raise ValueError(f"Failed to decrypt file: {str(e)}")
    
    # Create a temporary file with the same extension as the original
    file_ext = os.path.splitext(encrypted_file_path)[1]
    
    # Use delete=False so we can manage the file lifecycle ourselves
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_file_path = temp_file.name
    temp_file.close()  # Close it immediately to avoid issues with Windows file locks
    
    # Write the decrypted data to the temporary file
    with open(temp_file_path, 'wb') as file:
        file.write(decrypted_data)
    
    return temp_file_path

def decrypt_file_to_memory(encrypted_file_path):
    """
    Decrypt a file and return the content in memory
    
    Args:
        encrypted_file_path: Path to the encrypted file
        
    Returns:
        Bytes object containing the decrypted file content
    """
    if not os.path.exists(encrypted_file_path):
        raise FileNotFoundError(f"File {encrypted_file_path} not found")
    
    # Get the key
    key = get_encryption_key()
    fernet = Fernet(key)
    
    # Read the encrypted file
    with open(encrypted_file_path, 'rb') as file:
        encrypted_data = file.read()
    
    # Decrypt the data
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data
    except Exception as e:
        raise ValueError(f"Failed to decrypt file: {str(e)}")
