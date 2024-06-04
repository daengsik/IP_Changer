import json
import os

path = "preset.json"

with open(path, 'r') as file:
    data = json.load(file)

print(data[0]['name'])

test = os.getenv('APPDATA')
print(test)