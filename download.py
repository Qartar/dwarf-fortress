import re
import os
import requests
import subprocess
import zipfile

#-------------------------------------------------------------------------------
def version_tuple(version_text):
    """ Convert version string into a tuple that can be used for sorting """
    # Expected input "DF <Version> (<Date>)"
    m = re.match(r'DF ([\d.]+)(\w?)', version_text)
    version = [int(x) for x in m.group(1).split('.')]
    if len(m.group(2)):
        return version + [m.group(2)]
    else:
        return version

#-------------------------------------------------------------------------------
def extract_version_date(version_text):
    """ Extract date from the version string """
    # Expected input "DF <Version> (<Date>)"
    m = re.match(r'.*\((.*?)\)', version_text)
    return m.group(1) if m else 'now'

#-------------------------------------------------------------------------------
def download_versions():
    """ Return the html of the downloads page for extracting versions and packages """
    return requests.get('http://www.bay12games.com/dwarves/older_versions.html').text

#-------------------------------------------------------------------------------
def extract_versions(downloads_text):
    """ Parse the downloads page and return a list of release versions with their packages """
    versions_text = re.findall(r'<p class="menu">.*?</p>', downloads_text, re.DOTALL)

    version_pattern = re.compile(r'DF [\d.]+\w? \(.*?\)')
    package_pattern = re.compile(r'<a href="(.*?)">')

    platforms = {
        'legacy' : 'legacy',
        'windows' : 'win',
        'linux' : 'linux',
        'osx' : 'osx',
        # Only used briefly in 2008
        'mac' : 'm',
        # x86 packages after x64 release
        'legacy x86' : 'legacy32',
        'windows x86' : 'win32',
        'linux x86' : 'linux32',
        'osx x86' : 'osx32',
        # 'small' packages
        'small' : 's',
        'windows small' : 'win_s',
        'windows x86 small' : 'win32_s',
        'legacy x86 small' : 'legacy32_s',
    }

    # Build up the list of versions
    versions = []
    for v in versions_text:
        # Find the release name for this version
        version_match = version_pattern.search(v)
        if version_match is None:
            continue

        # Find all release packages for this version
        version_packages = package_pattern.findall(v)

        # Associate each package by its platform
        packages_dict = {}
        for package in version_packages:
            basename = package.split('.')[0]
            platform = ''
            for key, value in platforms.iteritems():
                if basename.endswith('_' + value):
                    platform = key
                    break
            packages_dict[platform] = package

        versions.append((version_match.group(0), packages_dict))

    # Return the versions, sorted by version number
    return sorted(versions, key = lambda x: version_tuple(x[0]))

#-------------------------------------------------------------------------------
def download_package(package_path, package_name):
    """ Download the package from bay12games.com """
    package = requests.get('http://www.bay12games.com/dwarves/{0}'.format(package_name))
    with open(package_path, 'wb') as f:
        f.write(package.content)

#-------------------------------------------------------------------------------
def extract_package(repository, package_path):
    """ Extract the package into the repository """
    with zipfile.ZipFile(package_path, 'r') as z:
        z.extractall(repository)

#-------------------------------------------------------------------------------
def remove_package(package_path):
    """ Remove the package (after unpacking) """
    os.remove(package_path)

#-------------------------------------------------------------------------------
def git_initialize(repository):
    """ Perform first time initialization of the repository """
    if os.path.exists(repository):
        # Detach from master branch so we can delete it
        subprocess.call(['git', 'checkout', '--detach', 'master'], cwd=repository)
        # Delete master branch and re-create it as an orphan
        subprocess.call(['git', 'branch', '-D', 'master'], cwd=repository)
        subprocess.call(['git', 'checkout', '--orphan', 'master'], cwd=repository)
    else:
        # Initialize a new repository
        subprocess.call(['git', 'init', repository])

#-------------------------------------------------------------------------------
def git_prepare(repository):
    """ Prepare the repository for a new package version """
    # Remove all untracked and ignored files in the repository
    subprocess.call(['git', 'clean', '-fdx'], cwd=repository)
    # Remove all indexed files in the repository
    subprocess.call(['git', 'rm', '-rf', './'], cwd=repository)

#-------------------------------------------------------------------------------
def git_commit(repository, message):
    """ Commit the state of the repository as a new commit """
    subprocess.call(['git', 'add', '.'], cwd=repository)
    subprocess.call(['git', 'commit',
                     '--author="Tarn Adams <toadyone@bay12games.com>"',
                     '--date="{0}"'.format(extract_version_date(message)),
                     '--message', message], cwd=repository)

#-------------------------------------------------------------------------------
def extract_release_notes(repository, summary):
    """ Extract release notes for the version in the repository """
    # Check if the release notes file exists
    if os.path.exists(os.path.join(repository, 'release notes.txt')):
        # Add release notes to index, otherwise Git won't recognize it on the first commit.
        subprocess.call(['git', 'add', 'release notes.txt'], cwd=repository)
        try:
            output = subprocess.check_output(['git', 'diff', 'HEAD', '--', 'release notes.txt'], cwd=repository)
            # Search for additions to the release notes file
            notes = re.search(r'^\+(Release notes for.*?(\r|\n|\r\n))(^\+.*?(\r|\n|\r\n))*', output, re.MULTILINE)
            # Remove the line addition markers from the diff
            lines = [x.lstrip('+') for x in notes.group(0).splitlines()]
            # Don't add extra line separators to the release notes
            last_index = len(lines)
            for idx in xrange(last_index, 0, -1):
                if lines[idx-1] == '' or lines[idx-1].startswith('****'):
                    last_index = idx-1
                else:
                    break
            # Combine the summary with the release notes
            return str('\n').join([summary, ''] + lines[0:last_index] + [''])

        except Exception as e:
            print str(e)

    # If file does not exist or extraction failed just use the summary
    return str('\n').join([summary, ''])

#-------------------------------------------------------------------------------
def main():
    repository_path = os.path.join('.', 'repo')

    print 'Downloading version list...'
    downloads_text = download_versions()

    print 'Parsing version list...'
    versions = extract_versions(downloads_text)

    print 'Initializing repository...'
    git_initialize(repository_path)

    for version, packages in versions:
        package_name = packages[''] if '' in packages else \
                       packages['legacy'] if 'legacy' in packages else None

        if package_name is None:
            raise Exception("Could not find appropriate package for version: {0}".format(version))

        package_path = os.path.join('.', package_name)

        if not os.path.exists(package_path):
            print 'Downloading package...'
            download_package(package_path, package_name)

        print 'Preparing repository...'
        git_prepare(repository_path)

        print 'Extracting package...'
        extract_package(repository_path, package_path)

        print 'Extracting release notes...'
        release_notes = extract_release_notes(repository_path, version)

        print 'Creating commit...'
        git_commit(repository_path, release_notes)

        print 'Removing package...'
        remove_package(package_path)

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
