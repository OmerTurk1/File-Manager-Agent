from tools import search_folder

print(search_folder("."))
print(search_folder(""))
print(search_folder("workspace"))
print(search_folder("./"))
print(search_folder(**{"folder_name":"."}))