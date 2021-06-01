from __future__ import division, print_function, unicode_literals

import base64
import json
from loguru import logger
import os
import pprint
from subprocess import CalledProcessError, check_output, PIPE, Popen, STDOUT

try:
    from urllib.parse import urlsplit, urlunsplit, splituser, urlunparse, urlparse
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen, splituser
    from urlparse import urlsplit, urlunsplit, urlunparse, urlparse

from .utils import force_link, ignore_missing_file, in_dir, TempDir, TempFile

MEDIA_TYPE = "application/vnd.git-lfs+json"
POST_HEADERS = {"Accept": MEDIA_TYPE, "Content-Type": MEDIA_TYPE}


def urlretrieve(url, data=None, headers=None):
    scheme, netloc, path, params, query, frag = urlparse(url)
    auth, host = splituser(netloc)
    if auth:
        auth = auth.encode("utf-8")
        url = urlunparse((scheme, host, path, params, query, frag))
        req = Request(url, data, headers)
        base64string = base64.encodebytes(auth)[:-1]
        basic = "Basic " + base64string.decode("utf-8")
        req.add_header("Authorization", basic)
    else:
        req = Request(url, data, headers)
    return urlopen(req)


def git_show(git_repo, p):
    with in_dir(git_repo):
        return check_output(["git", "show", "HEAD:" + p])


def get_cache_dir(git_dir, oid):
    return git_dir + "/lfs/objects/" + oid[:2] + "/" + oid[2:4]


def get_lfs_endpoint_url(git_repo, checkout_dir):
    try:
        with in_dir(checkout_dir):
            url = check_output("git config -f .lfsconfig --get lfs.url".split()).strip().decode("utf8")
    except CalledProcessError:
        with in_dir(git_repo):
            url = check_output("git config --get remote.origin.url".split()).strip().decode("utf8")
    if url.endswith("/"):
        url = url[:-1]
    if not url.endswith("/info/lfs"):
        url += "/info/lfs" if url.endswith(".git") else ".git/info/lfs"
    url_split = urlsplit(url)
    host, path = url_split.hostname, url_split.path
    if url_split.scheme != "https":
        if not url_split.scheme:
            # SSH format: git@example.org:repo.git
            host, path = url.replace("/info/lfs", "").split(":", 1)
            auth_header, url = get_lfs_api_token(host, path)
            assert url
            return url, auth_header
        url = urlunsplit(("https", host, path, "", ""))

    # need to get GHE auth token if available. issue cmd like this to get:
    # ssh git@git-server.com git-lfs-authenticate foo/bar.git download
    if path.endswith("/info/lfs"):
        path = path[: -len("/info/lfs")]

    auth_header = {}
    if not (url_split.username and url_split.password):
        # TODO: this is ugly
        try:
            auth_header, remote_path = get_lfs_api_token("git@" + host, path)
            if remote_path:
                assert url == remote_path
        except:
            pass
    return url, auth_header


def get_lfs_api_token(host, path):
    """gets an authorization token to use to do further introspection on the
    LFS info in the repository.   See documentation here for description of
    the ssh command and response:
    https://github.com/git-lfs/git-lfs/blob/master/docs/api/server-discovery.md
    """
    header_info = {}
    query_cmd = "ssh " + host + " git-lfs-authenticate " + path + " download"
    # TODO: we're suppressing stderr
    output = check_output(query_cmd.split(), stderr=PIPE).strip().decode("utf8")
    if output:
        query_resp = json.loads(output)
        header_info = query_resp["header"]
        url = query_resp["href"]

    return header_info, url


def find_lfs_files(checkout_dir):
    """Yields the paths of the files managed by Git LFS"""
    with in_dir(checkout_dir):
        repo_files = Popen("git ls-files -z".split(), stdout=PIPE)
        repo_files_attrs = check_output(
            "git check-attr --cached --stdin -z diff filter".split(),
            stdin=repo_files.stdout,
        )
    # In old versions of git, check-attr's `-z` flag only applied to input
    sep = b"\0" if b"\0" in repo_files_attrs else b"\n"
    i = iter(repo_files_attrs.strip(sep).split(sep))
    paths = set()
    while True:
        try:
            if sep == b"\0":
                path, _, value = next(i), next(i), next(i)
            else:
                split_line = next(i).rsplit(b": ", 2)
                if len(split_line) == 3:
                    path, _, value = split_line
                else:
                    continue
        except StopIteration:
            break
        if value != b"lfs":
            continue
        if path in paths:
            continue
        paths.add(path)
        yield path.decode("ascii")


def read_lfs_metadata(checkout_dir, only=None):
    """Yields (path, oid, size) tuples for all files managed by Git LFS"""
    for path in find_lfs_files(checkout_dir):
        if only is not None and path not in only:
            continue
        meta = git_show(checkout_dir, path).decode("utf8").strip().split("\n")
        if meta[0] != "version https://git-lfs.github.com/spec/v1":
            continue
        d = dict(line.split(" ", 1) for line in meta[1:])
        oid = d["oid"]
        oid = oid[7:] if oid.startswith("sha256:") else oid
        size = int(d["size"])
        yield (path, oid, size)


def fetch_urls(lfs_url, lfs_auth_info, oid_list):
    """Fetch the URLs of the files from the Git LFS endpoint"""
    data = json.dumps({"operation": "download", "objects": oid_list})
    headers = dict(POST_HEADERS)
    headers.update(lfs_auth_info)
    resp = json.loads(urlretrieve(lfs_url + "/objects/batch", data.encode("ascii"), headers).read().decode("ascii"))
    assert "objects" in resp, resp
    return resp["objects"]


def fetch(git_repo, checkout_dir=None, only=None):
    """Download and smudge files managed by Git LFS
    :param git_repo: path to the root of a git working directory (the parent directory of the .git directory),
                     or to the .git directory itself
    :param checkout_dir: optional path specifying where the repository is checked out
    :param only: optional list of files to be checked out. By default, all files will be fetched
    """
    git_dir = git_repo + "/.git" if os.path.isdir(git_repo + "/.git") else git_repo
    checkout_dir = checkout_dir or git_repo
    if checkout_dir == git_dir:
        logger.error("Can't checkout into a bare repo, please provide a valid checkout_dir")
        raise SystemExit(1)
    checkout_git_dir = checkout_dir + "/.git"
    if not os.path.isdir(checkout_git_dir):
        with TempDir(dir=checkout_dir) as d:
            check_output(["git", "clone", "-ns", git_repo, d], stderr=STDOUT)
            os.rename(d + "/.git", checkout_git_dir)
            with in_dir(checkout_dir):
                check_output(["git", "reset", "HEAD"])

    # Read the LFS metadata
    found = False
    if only is None:
        only = []
    only_enabled = len(only) > 0
    only = [os.path.relpath(os.path.abspath(path), checkout_dir) for path in only]
    oid_list, lfs_files = [], {}
    for path, oid, size in read_lfs_metadata(checkout_dir, only=only):
        if only_enabled:
            if path not in only:
                continue
            else:
                only.remove(path)

        found = True
        dst = checkout_dir + "/" + path

        # Skip the file if it looks like it's already there
        with ignore_missing_file():
            if os.stat(dst).st_size == size:
                logger.trace(f"Skipping {path} (already present)")
                continue

        # If we have the file in the cache, link to it
        with ignore_missing_file():
            cached = get_cache_dir(git_dir, oid) + "/" + oid
            if os.stat(cached).st_size == size:
                force_link(cached, dst)
                logger.debug(f"Linked {path} from the cache")
                continue

        oid_list.append(dict(oid=oid, size=size))
        lfs_files[(oid, size)] = path

    if only_enabled and only:
        logger.error("Couldn't find the following files requested with --only:")
        for path in only:
            logger.error(path)
        return False

    if not found:
        logger.error("This repository does not seem to use LFS.")
        return False

    if not oid_list:
        logger.debug("Nothing to fetch.")
        return True

    # Fetch the URLs of the files from the Git LFS endpoint
    lfs_url, lfs_auth_info = get_lfs_endpoint_url(git_repo, checkout_dir)

    logger.debug(f"Fetching URLs from {lfs_url} ...")
    logger.trace(f"Authorization info for URL: {lfs_auth_info}")
    logger.trace(f"oid_list: {pprint.pformat(oid_list)}")
    objects = fetch_urls(lfs_url, lfs_auth_info, oid_list)

    # Download the files
    tmp_dir = git_dir + "/lfs/tmp"
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    for obj in objects:
        oid, size = (obj["oid"], obj["size"])
        path = lfs_files[(oid, size)]
        cache_dir = get_cache_dir(git_dir, oid)

        # Download into tmp_dir
        with TempFile(dir=tmp_dir) as f:
            url = obj["actions"]["download"]["href"]
            head = obj["actions"]["download"]["header"]
            logger.info(f"Downloading {path} ({(size / (1024 ** 2)):.2f} MB) from {url}...")
            h = urlretrieve(url, headers=head)
            while True:
                buf = h.read(10240)
                if not buf:
                    break
                f.write(buf)

            # Move to cache_dir
            dst1 = cache_dir + "/" + oid
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            logger.trace("temp download file: " + f.name)
            logger.trace("cache file name: " + dst1)
            os.rename(f.name, dst1)

        # Copy into checkout_dir
        dst2 = checkout_dir + "/" + path
        force_link(dst1, dst2)

    return True
