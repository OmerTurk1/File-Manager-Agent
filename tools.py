import os
import shutil
from typing import Dict, List, Union
from dotenv import load_dotenv

load_dotenv()

MAIN_ROOT_FOLDER = os.getenv("MAIN_ROOT_FOLDER") 

VIEWABLE_FOLDER_ROOT = os.getenv("VIEWABLE_FOLDER_ROOT") 

if not MAIN_ROOT_FOLDER or not VIEWABLE_FOLDER_ROOT:
    raise ValueError("Environment variables MAIN_ROOT_FOLDER and VIEWABLE_FOLDER_ROOT must be set!")

# --- TAGS ---
def register_tool(func):
    func.is_tool = True
    return func

# --- CORE FUNCTIONS ---

def _resolve_and_validate_path(path_str: str, allowed_root: str) -> str:
    """
    Verilen yol ifadesini güvenli bir şekilde absolute path'e çevirir ve 
    belirtilen kök dizinin (root) dışına çıkılmadığını (Path Traversal) doğrular.
    """
    if os.path.isabs(path_str):
        full_path = os.path.normpath(path_str)
    else:
        full_path = os.path.normpath(os.path.join(allowed_root, path_str))
    
    real_allowed_root = os.path.realpath(allowed_root)
    real_full_path = os.path.realpath(full_path)
    
    if not real_full_path.startswith(real_allowed_root):
        raise PermissionError(f"Access Denied: Path '{path_str}' is outside the permitted boundary.")
        
    return real_full_path

def _resolve_read_path(path_str: str) -> str:
    """
    Okuma işlemleri için yolu doğrular. 
    1. Önce MAIN_ROOT_FOLDER üzerinde yolu çözümler ve dosya/klasör gerçekten VAR MI diye bakar.
    2. Eğer MAIN_ROOT_FOLDER içinde yoksa veya yetki hatası alınırsa, VIEWABLE_FOLDER_ROOT dizinine bakar.
    """
    try:
        main_path = _resolve_and_validate_path(path_str, MAIN_ROOT_FOLDER)
        if os.path.exists(main_path):
            return main_path
    except PermissionError:
        pass

    try:
        viewable_path = _resolve_and_validate_path(path_str, VIEWABLE_FOLDER_ROOT)
        return viewable_path
    except PermissionError:
        raise PermissionError(f"Access Denied: '{path_str}' is outside both permitted roots.")
    
# --- TOOL FUNCTIONS ---

@register_tool
def create_element(element_name: str, file_type: str, location: str = "") -> str:
    """
    Create a file or folder at a given location within the workspace.

    Parameters:
        element_name (str): Name of the element to create, or its relative path.
        file_type (str): Type of element. Expected values are 'file' or 'folder'.
        location (str): Optional target folder path where the element should be created.

    Returns:
        str: A success message or an error description.
    """
    try:
        
        base_dir = _resolve_and_validate_path(location, MAIN_ROOT_FOLDER)
        
        
        target_path = _resolve_and_validate_path(os.path.join(base_dir, element_name), MAIN_ROOT_FOLDER)
        
        if file_type.lower() == 'folder':
            os.makedirs(target_path, exist_ok=True)
            return f"Success: Folder created successfully at '{target_path}'."
        elif file_type.lower() == 'file':
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'a', encoding='utf-8'):
                os.utime(target_path, None)  
            return f"Success: File created successfully at '{target_path}'."
        else:
            return f"Error: Invalid file_type '{file_type}'. Expected 'file' or 'folder'."
            
    except Exception as e:
        return f"Error creating element: {str(e)}"

@register_tool
def write_file(file_name: str, content: str) -> str:
    """
    Write string content into a file within the workspace. Overwrites if file exists.

    Parameters:
        file_name (str): Name or relative path of the file to write.
        content (str): Text content to write into the file.

    Returns:
        str: A success message or an error description.
    """
    try:
        target_path = _resolve_and_validate_path(file_name, MAIN_ROOT_FOLDER)
        
        
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Success: Content written to file '{file_name}' successfully."
    except Exception as e:
        return f"Error writing to file: {str(e)}"

@register_tool
def empty_file(file_name: str) -> str:
    """
    Clear the contents of a file within the workspace.

    Parameters:
        file_name (str): Name or relative path of the file to truncate.

    Returns:
        str: A success message or an error description.
    """
    try:
        target_path = _resolve_and_validate_path(file_name, MAIN_ROOT_FOLDER)
        
        if not os.path.exists(target_path):
            return f"Error: File '{file_name}' does not exist."
        if os.path.isdir(target_path):
            return f"Error: '{file_name}' is a directory, cannot empty it as a file."
            
        with open(target_path, 'w', encoding='utf-8') as f:
            f.truncate(0)
            
        return f"Success: File '{file_name}' has been cleared."
    except Exception as e:
        return f"Error emptying file: {str(e)}"

@register_tool
def delete_element(element_name: str) -> str:
    """
    Delete a file or folder within the workspace.

    Parameters:
        element_name (str): Name or relative path of the element to delete.

    Returns:
        str: A success message or an error description.
    """
    try:
        target_path = _resolve_and_validate_path(element_name, MAIN_ROOT_FOLDER)
        
        if not os.path.exists(target_path):
            return f"Error: Element '{element_name}' does not exist."
            
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
            return f"Success: Folder '{element_name}' and all its contents deleted successfully."
        else:
            os.remove(target_path)
            return f"Success: File '{element_name}' deleted successfully."
            
    except Exception as e:
        return f"Error deleting element: {str(e)}"

@register_tool
def read_file(file_name: str) -> str:
    """
    Read and return the text content of a file from allowed viewable roots or workspace.

    Parameters:
        file_name (str): Name or relative path of the file to read.

    Returns:
        str: The contents of the file, or an error message.
    """
    try:
        target_path = _resolve_read_path(file_name)
        
        if not os.path.exists(target_path):
            return f"Error: File '{file_name}' not found in workspace or viewable system folders."
        if os.path.isdir(target_path):
            return f"Error: '{file_name}' is a directory, use search_folder to view its contents."
            
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
            
    except Exception as e:
        return f"Error reading file: {str(e)}"

@register_tool
def search_folder(folder_name: str) -> Union[List[str], str]:
    """
    Return a structured flat list of a folder's contents (files and subfolders).

    Parameters:
        folder_name (str): Name or relative path of the folder to search.

    Returns:
        list or str: List of items inside the folder, or an error message string.
    """
    try:
        if folder_name in ["", ".", "./"]:
            target_path = MAIN_ROOT_FOLDER
        else:
            target_path = _resolve_read_path(folder_name)
        
        if not os.path.exists(target_path):
            return f"Error: Folder '{folder_name}' not found in workspace or viewable system folders."
        if not os.path.isdir(target_path):
            return f"Error: '{folder_name}' is a file, not a folder."
            
        return os.listdir(target_path)
        
    except Exception as e:
        return f"Error searching folder: {str(e)}"

@register_tool
def move_file(file_name: str, new_location: str) -> str:
    """
    Move a file or folder to a new destination within the workspace.

    Parameters:
        file_name (str): Name or relative path of the file/folder to move.
        new_location (str): Destination folder path or new relative path for the file.

    Returns:
        str: A success message or an error description.
    """
    try:
        source_path = _resolve_read_path(file_name)
        target_dir = _resolve_and_validate_path(new_location, MAIN_ROOT_FOLDER)
        
        if not os.path.exists(source_path):
            return f"Error: Source element '{file_name}' does not exist."
        
        if os.path.isdir(target_dir) and not new_location.endswith(os.path.basename(source_path)):
            destination_path = os.path.join(target_dir, os.path.basename(source_path))
        else:
            destination_path = target_dir
            
        destination_path = _resolve_and_validate_path(destination_path, MAIN_ROOT_FOLDER)
        
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        shutil.move(source_path, destination_path)
        return f"Success: Moved '{file_name}' to '{destination_path}' successfully."
        
    except Exception as e:
        return f"Error moving element: {str(e)}"