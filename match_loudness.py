from autoscrub import *

os.chdir('C:\\Users\\rander\\Videos')
mp4s = [x for x in os.listdir('.') if x.lower().endswith('.mp4') and 'processed' not in x]

for path in mp4s:
	matchLoudness(path, -18)