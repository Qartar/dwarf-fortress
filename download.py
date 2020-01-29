import re
import os
import urllib.request
import subprocess
import zipfile
import tarfile
import shutil
from itertools import chain

git = 'C:/Program Files/Git/bin/git.exe'

PLATFORMS = {
    'legacy' : 'legacy',
    'windows' : 'win',
    'linux' : 'linux',
    'osx' : 'osx',
    # Only used briefly in 2008
    'mac' : 'm',
    # x86 packages after x64 release
    'legacy-x86' : 'legacy32',
    'windows-x86' : 'win32',
    'linux-x86' : 'linux32',
    'osx-x86' : 'osx32',
    # 'small' packages
    'small' : 's',
    'legacy-small' : 'legacy_s',
    'windows-small' : 'win_s',
    'windows-x86-small' : 'win32_s',
    'legacy-x86-small' : 'legacy32_s',
}

BRANCHES = {
    'legacy' : {
        'platforms' : ['legacy', '']
    },
    'windows' : {
        'parent' : 'legacy',
        'platforms' : ['windows'],
    },
    'linux' : {
        'parent' : 'legacy',
        'platforms' : ['linux'],
    },
    'osx' : {
        'parent' : 'legacy',
        'platforms' : ['osx'],
    },
    # x86 versions
    'legacy-x86' : {
        'parent' : 'legacy',
        'platforms' : ['legacy-x86'],
    },
    'windows-x86' : {
        'parent' : 'windows',
        'platforms' : ['windows-x86'],
    },
    'linux-x86' : {
        'parent' : 'linux',
        'platforms' : ['linux-x86'],
    },
    'osx-x86' : {
        'parent' : 'osx',
        'platforms' : ['osx-x86'],
    },
    # small versions
    'legacy-small' : {
        'parent' : 'legacy',
        'platforms' : ['legacy-small', 'small'],
    },
    'windows-small' : {
        'parent' : 'legacy-small',
        'platforms' : ['windows-small'],
    },
    'legacy-x86-small' : {
        'parent' : 'legacy-small',
        'platforms' : ['legacy-x86-small'],
    },
    'windows-x86-small' : {
        'parent' : 'windows-small',
        'platforms' : ['windows-x86-small'],
    },
}

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
    return urllib.request.urlopen('http://www.bay12games.com/dwarves/older_versions.html').read().decode('utf-8')

#-------------------------------------------------------------------------------
def repair_versions(versions_text):
    """ """
    for v in versions_text:
        start = 0
        while start >= 0:
            end = v.find(r'<p class="menu">', start + 1)
            yield v[start:end]
            start = end

#-------------------------------------------------------------------------------
def extract_versions(downloads_text):
    """ Parse the downloads page and return a list of release versions with their packages """
    versions_text = re.findall(r'<p class="menu">.*?</p>', downloads_text, re.DOTALL)

    version_pattern = re.compile(r'DF [\d.]+\w? \(.*?\)')
    package_pattern = re.compile(r'<a href="(.*?)">')

    # Build up the list of versions
    versions = []
    for v in repair_versions(versions_text):
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
            platform_value = ''
            for key, value in PLATFORMS.items():
                if len(value) > len(platform_value) and basename.endswith('_' + value):
                    platform = key
                    platform_value = value
            packages_dict[platform] = package

        versions.append((version_match.group(0), packages_dict))

    # Return the versions, sorted by version number
    return sorted(versions, key = lambda x: version_tuple(x[0]))

#-------------------------------------------------------------------------------
def download_package(package_path, package_name):
    """ Download the package from bay12games.com """
    try:
        package = urllib.request.urlopen('http://www.bay12games.com/dwarves/{0}'.format(package_name))
        with open(package_path, 'wb') as f:
            f.write(package.read())
    except urllib.error.HTTPError as e:
        # 0.47.01 renamed 64-bit "legacy" packages to "legacy64" but did not update download URL
        package64_name = package_name.replace('legacy', 'legacy64')
        package = urllib.request.urlopen('http://www.bay12games.com/dwarves/{0}'.format(package64_name))
        with open(package_path, 'wb') as f:
            f.write(package.read())

#-------------------------------------------------------------------------------
def extract_package(repository, package_path):
    """ Extract the package into the repository """
    if os.path.splitext(package_path)[1] == '.zip':
        with zipfile.ZipFile(package_path, 'r') as z:
            z.extractall(repository)
    elif os.path.splitext(package_path)[1] == '.bz2':
        with tarfile.open(package_path, 'r:bz2') as t:
            prefix = os.path.commonprefix(t.getnames())
            for m in t.getmembers():
                if m.name != prefix:
                    m.name = m.name.replace(prefix, '.')
                    t.extract(m, repository)
    else:
        raise 'Unrecognized package format'

#-------------------------------------------------------------------------------
def remove_package(package_path):
    """ Remove the package (after unpacking) """
    os.remove(package_path)

#-------------------------------------------------------------------------------
def git_initialize(repository):
    """ Perform first time initialization of the repository """
    if os.path.exists(repository):
        # Detach from master branch so we can delete it
        subprocess.call([git, 'checkout', '--detach', 'master'], cwd=repository)
        # Delete master branch and re-create it as an orphan
        subprocess.call([git, 'branch', '-D', 'master'], cwd=repository)
        subprocess.call([git, 'checkout', '--orphan', 'master'], cwd=repository)
    else:
        # Initialize a new repository
        subprocess.call([git, 'init', repository])

#-------------------------------------------------------------------------------
def git_prepare(repository):
    """ Prepare the repository for a new package version """
    # Remove all untracked and ignored files in the repository
    subprocess.call([git, 'clean', '-fdx'], cwd=repository)
    # Remove all indexed files in the repository
    subprocess.call([git, 'rm', '-rf', '.'], cwd=repository)

#-------------------------------------------------------------------------------
def git_commit(repository, message):
    """ Commit the state of the repository as a new commit """
    subprocess.call([git, 'add', '.'], cwd=repository)
    p = subprocess.Popen([git, 'commit',
                          '--author="Tarn Adams <toadyone@bay12games.com>"',
                          '--date="{0}"'.format(extract_version_date(message)),
                          '--file', '-'], stdin=subprocess.PIPE, cwd=repository)
    p.communicate(input=message.encode('utf-8'))

#-------------------------------------------------------------------------------
def git_list_versions(repository, branch):
    """ Return a dictionary of all versions that have been added to the repository with their commit hashes """
    try:
        commits = subprocess.check_output([git, 'log', '--oneline', branch, '--'], cwd=repository)
        return dict([reversed(x.split(None, 1)) for x in commits.decode('utf-8').splitlines()])
    except:
        print("git_list_versions() failed")
        return dict()

#-------------------------------------------------------------------------------
def extract_release_notes(repository, summary):
    """ Extract release notes for the version in the repository """
    # Check if the release notes file exists
    if os.path.exists(os.path.join(repository, 'release notes.txt')):
        # Add release notes to index, otherwise Git won't recognize it on the first commit.
        subprocess.call([git, 'add', 'release notes.txt'], cwd=repository)
        try:
            output = subprocess.check_output([git, 'diff', '--cached', 'release notes.txt'], cwd=repository)
            # Search for additions to the release notes file
            notes = re.search(r'^\+(Release notes for.*?(\r|\n|\r\n))(^\+.*?(\r|\n|\r\n))*', output.decode('utf-8'), re.MULTILINE)
            # Remove the line addition markers from the diff
            lines = [x.lstrip('+') for x in notes.group(0).splitlines()]
            # Don't add extra line separators to the release notes
            last_index = len(lines)
            for idx in range(last_index, 0, -1):
                if lines[idx-1] == '' or lines[idx-1].startswith('****'):
                    last_index = idx-1
                else:
                    break
            # Combine the summary with the release notes
            return str('\n').join([summary, ''] + lines[0:last_index] + [''])

        except Exception as e:
            print(str(e))

    # If file does not exist or extraction failed just use the summary
    return str('\n').join([summary, ''])

#-------------------------------------------------------------------------------
def git_check_branch(repository, branch):
    """ Return true if the branch already exists in the repository """
    output = subprocess.check_output([git, 'branch', '--list', branch], cwd=repository)
    return True if branch in output.decode('utf-8').split() else False

#-------------------------------------------------------------------------------
def git_initialize_branch(repository, branch, parent = None):
    """ Initialize the branch into a new worktree and return the worktree path """
    worktree = os.path.join(repository, branch)

    if git_check_branch(repository, branch):
        # If the branch already exists then just check it out as-is into a worktree
        subprocess.call([git, 'worktree', 'add', branch, branch], cwd=repository)
    elif parent is None:
        # If the branch does not exist and does not have a parent then create a new orphan branch
        subprocess.call([git, 'worktree', 'add', '--detach', branch], cwd=repository)
        subprocess.call([git, 'checkout', '--orphan', branch], cwd=worktree)
        # Delete any files that were left around from orphaning
        subprocess.call([git, 'rm', '-rf', '.'], cwd=worktree, stderr=None)
    else:
        # If the branch does not exist but has a parent then create a new branch starting at parent
        subprocess.call([git, 'worktree', 'add', '-b', branch, branch, parent], cwd=repository)

    # Return the path to the branch worktree
    return worktree

#-------------------------------------------------------------------------------
def git_finalize_branch(repository, branch):
    """ Clean up the branch worktree """
    if os.path.exists(os.path.join(repository, branch)):
        shutil.rmtree(os.path.join(repository, branch))
        subprocess.call([git, 'worktree', 'prune'])

#-------------------------------------------------------------------------------
def filter_platform_packages(platforms, versions):
    """ Return a dictionary of packages keyed by version for the given platforms """
    for version, packages in versions:
        for platform in platforms:
            if platform in packages:
                yield version, packages[platform]
                break

#-------------------------------------------------------------------------------
def filter_branch_packages(branch, versions):
    """ Return a dictionary of packages keyed by version for the given branch """
    branch_platforms = BRANCHES[branch]['platforms']
    branch_packages = filter_platform_packages(branch_platforms, versions)

    if 'parent' in BRANCHES[branch]:
        parent_branch = BRANCHES[branch]['parent']
        parent_platforms = BRANCHES[parent_branch]['platforms']
        parent_packages = filter_platform_packages(parent_platforms, versions)

        branch_packages = list(branch_packages)
        # Filter out all packages on the parent branch with the same or later version than the earliest package on the child branch
        filter_version = version_tuple(branch_packages[0][0])
        filter_packages = filter(lambda x: version_tuple(x[0]) < filter_version, parent_packages)
        return chain(branch_packages, filter_packages)
    else:
        return branch_packages

#-------------------------------------------------------------------------------
def git_parent_commit(repository, parent_branch, version):
    """ Return the commit hash for the given version on the given branch """
    git_versions = git_list_versions(repository, parent_branch)
    return git_versions[version]

#-------------------------------------------------------------------------------
def find_common_ancestor(parent_branch, child_branch, versions):
    """ Return the version of the most recent package which is included by both branches """
    # Find all of the packages included in either branch
    parent_packages = set(filter_branch_packages(parent_branch, versions))
    child_packages = set(filter_branch_packages(child_branch, versions))
    # Find all of the packages included in both branches
    shared_packages = set(x[1] for x in parent_packages & child_packages)
    # Create a mapping of packages to versions
    package_versions = dict((x[1], x[0]) for x in chain(parent_packages, child_packages))
    # Common ancestor is the most recent package included in both branches
    common_package = sorted(shared_packages, key=lambda x: version_tuple(package_versions[x]))[-1] if len(shared_packages) else None
    return package_versions[common_package] if common_package else None

#-------------------------------------------------------------------------------
def populate_branch(repository, branch, versions):
    """ Add packages to the repository for the given branch and versions """
    # Get list of packages and versions for this branch
    branch_platforms = BRANCHES[branch]['platforms']
    branch_packages = dict(filter_platform_packages(branch_platforms, versions))

    # Get list of versions that have already been committed to this branch
    git_versions = git_list_versions(repository, branch)
    # Get list of versions that have NOT been committed to this branch
    new_versions = set(branch_packages.keys()) - set(git_versions.keys())

    if len(new_versions) == 0:
        return

    # Sort list of uncommitted versions by version number
    sorted_versions = sorted(new_versions, key = version_tuple)

    if 'parent' in BRANCHES[branch]:
        parent_branch = BRANCHES[branch]['parent']

        # Make sure that parent branch is up to date first
        populate_branch(repository, parent_branch, versions)

        # Find the commit hash for the last package shared between this branch and its parent
        common_ancestor = find_common_ancestor(parent_branch, branch, versions)
        parent_commit = git_parent_commit(repository, parent_branch, common_ancestor)

        # Initialize this branch starting from the common ancestor
        worktree = git_initialize_branch(repository, branch, parent_commit)
    else:
        # Initialize this branch as an orphan
        worktree = git_initialize_branch(repository, branch)

    print('Populating branch: \'' + branch + '\'...')

    for version in sorted_versions:
        # Look up the branch package by version
        package_name = branch_packages[version]
        package_path = os.path.join('..', package_name)

        if not os.path.exists(package_path):
            print('Downloading package...')
            download_package(package_path, package_name)

        print('Preparing repository...')
        git_prepare(worktree)

        print('Extracting package...')
        extract_package(worktree, package_path)

        print('Extracting release notes...')
        release_notes = extract_release_notes(worktree, version)

        print('Creating commit...')
        git_commit(worktree, release_notes)

        print('Removing package...')
        #remove_package(worktree)

    git_finalize_branch(repository, branch)

#-------------------------------------------------------------------------------
def main():
    repository_path = '.'

    print('Downloading version list...')
    downloads_text = download_versions()

    print('Parsing version list...')
    versions = extract_versions(downloads_text)

    print('Updating repository...')
    #git_initialize(repository_path)

    for branch in BRANCHES.keys():
        populate_branch(repository_path, branch, versions)

#-------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
