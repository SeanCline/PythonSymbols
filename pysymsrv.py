"""Downloads all Python symbols and checks them into a symbol server."""

import sys, os, subprocess, logging, shutil, re, urllib.request, urllib.parse, json
import symstore

_logger = logging.getLogger(__name__)

def fetch_page(url):
    """Fetchs a the contents at a URL as a string."""
    _logger.info("Fetching %r...", url)
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode(resp.headers.get_content_charset("utf-8"))


def download_file(source_url, destination_filename):
    """Downloads a file at the provided url, to the destination on disk."""
    _logger.info("Downloading %r to %r...", source_url, destination_filename)
    with urllib.request.urlopen(source_url) as resp, open(destination_filename, 'wb') as destination_file:
        shutil.copyfileobj(resp, destination_file)


def get_available_python_versions():
    """Returns a list of python versions available from python.org."""
    indexhtml = fetch_page("https://www.python.org/ftp/python/")
    return re.findall(r"<a\s+href=\"(\d+\.\d+(?:\.\d+)?)\/?\"\s*>", indexhtml)


def read_stored_versions(filename="versions.json"):
    """Reads the list of Python versions that have already been added to the store."""
    try:
        with open(filename, "r") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return []


def save_stored_versions(versions, filename="versions.json"):
    """Saves the list of python versions in the store to disk."""
    with open(filename, "w") as fp:
        json.dump(list(versions), fp)


def download_pdbs_for_version(version, target_dir):
    """Downloads the debugging symbols for a given version of Python."""
    base_url = urllib.parse.urljoin("https://www.python.org/ftp/python/", version + "/")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        os.makedirs(os.path.join(target_dir, "win32"))
        os.makedirs(os.path.join(target_dir, "amd64"))
    
    archives = [
        "python-" + version + "-pdb.zip", # Python 2.x
        "python-" + version + ".amd64-pdb.zip", # Python 2.x
        "win32/core_pdb.msi", # Python 3.x
        "win32/exe_pdb.msi", # Python 3.x
        "win32/lib_pdb.msi", # Python 3.x
        "win32/tkltk_pdb.msi", # Python 3.x
        "win32/test_pdb.msi", # Python 3.x
        "amd64/core_pdb.msi", # Python 3.x
        "amd64/exe_pdb.msi", # Python 3.x
        "amd64/lib_pdb.msi", # Python 3.x
        "amd64/tkltk_pdb.msi", # Python 3.x
        "amd64/test_pdb.msi", # Python 3.x
    ]
    
    for archive in archives:
        source_url = urllib.parse.urljoin(base_url, archive)
        destination_filename = os.path.join(target_dir, archive)
        try:
            download_file(source_url, destination_filename)
        except urllib.error.HTTPError:
            _logger.info("Failed to download: %r", source_url)
            pass # Just keep going.


def extract_archive(archive_filename):
    """Unzips zip files and MSIs."""
    _logger.info("Extracting: %r...", archive_filename)
    absolute_path = os.path.abspath(archive_filename)
    targetdir = os.path.splitext(absolute_path)[0]
    subprocess.call(["7z", "x", absolute_path, "-o" + targetdir])


def extract_archives_in_direcory(path):
    """Recursively extracts all of the zipped/MSI'd files in a provided directory."""
    for root, subdirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            extract_archive(file_path)


def store_pdbs_in_direcory(pdb_path, store_path, version_comment):
    """Recursively adds all of the pdb files in a provided directory to the symbols store."""
    sym_store = symstore.Store(store_path)
    transaction = sym_store.new_transaction("CPython", version_comment)
    num_files_stored = 0
    for root, subdirs, files in os.walk(pdb_path):
        for file in files:
            if file.endswith(".pdb"):
                file_path = os.path.join(root, file)
                transaction.add_file(file_path, symstore.cab.compression_supported)
                num_files_stored += 1
    if num_files_stored > 0:
        sym_store.commit(transaction)

    
def fetch_and_store_pdbs_for_version(version):
    temp_folder = version + "-temp/"
    store_folder = "./symbols"
    download_pdbs_for_version(version, temp_folder)
    extract_archives_in_direcory(temp_folder)
    store_pdbs_in_direcory(temp_folder, store_folder, version)
    shutil.rmtree(temp_folder)
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    available_versions = get_available_python_versions()
    _logger.info("Versions available from Python.org: %r", available_versions)

    stored_versions = read_stored_versions();
    _logger.info("Versions already stored: %r", stored_versions)
    
    needed_versions = set(available_versions) - set(stored_versions)
    _logger.info("Need to fetch symbols for versions: %r", needed_versions)
    
    for version in needed_versions:
        fetch_and_store_pdbs_for_version(version)
        stored_versions.append(version)
        save_stored_versions(stored_versions)