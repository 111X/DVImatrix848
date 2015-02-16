
from distutils.version import LooseVersion

def stripVersionString(version_string):
    if version_string.startswith('v'):
	version_string=version_string[1:]
    return version_string.strip()

def getLatestVersion(j):
	v=None
	for k in j:
		version_string=stripVersionString(k['tag_name'])
		vnew=LooseVersion(version_string)
		if not v:
			v=vnew
		else:
			
			if vnew > v:
				v=vnew
	if v:
		return str(v)
	return None
def getGithubVersion(project):
    import requests
    url=("https://api.github.com/repos/%s/releases" % project)
    r=requests.get(url)
    return getLatestVersion(r.json())

def getCurrentVersion():
    import subprocess
    tagname=subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0'])
    return stripVersionString(tagname)
                                    

if __name__ == '__main__':
    current_version=getCurrentVersion()
    github_version=getGithubVersion("iem-projects/DVImatrix848")
    if LooseVersion(current_version) < LooseVersion(github_version):
        print("new version available: %s" % (github_version))

    True
