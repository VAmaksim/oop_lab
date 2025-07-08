import json

with open('font.json', 'r') as file:
    info = json.load(file)
with open('font.txt', 'w') as file:
    for sym in info.values():
        for line in sym:
            file.write(line)
            file.write('\n')
        file.write('-' * 15 + '\n')
