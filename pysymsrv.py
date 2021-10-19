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


def try_download_file(source_url, destination_filename, already_downloaded_files):
    """Downloads a file at the provided url and adds it to the set of downloaded archives if it hasn't already been downloaded."""
    # If we've already downloaded the file, then it's already in the symbol store.
    if source_url in already_downloaded_files:
        _logger.info("Skipping already downloaded file: %r", source_url)
        return
    
    try:
        download_file(source_url, destination_filename)
        already_downloaded_files.add(source_url)
    except urllib.error.HTTPError as err:
        _logger.info("Failed to download: %r", source_url)
        
        if err.code == 404:
            already_downloaded_files.add(source_url) # Mark file-not-found as downloaded.
        pass # Just keep going.


def get_available_python_versions(root):
    """Returns a list of python versions available from python.org."""
    indexhtml = fetch_page(root)
    return re.findall(r"<a\s+href=\"(\d+\.\d+(?:\.\d+)?)\/?\"\s*>", indexhtml)


def read_downloaded_files_list(filename="downloaded.json"):
    """Reads the list of archives that have already been added to the store."""
    try:
        with open(filename, "r") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return []


def save_downloaded_files_list(files, filename="downloaded.json"):
    """Saves the list of archives we've already download to disk."""
    with open(filename, "w") as fp:
        json.dump(list(files), fp)


def download_pdbs_for_version(root, version, target_dir, already_downloaded_files):
    """Downloads the debugging symbols for a given version of Python."""    
    base_url = urllib.parse.urljoin(root, version + "/")
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
        try_download_file(source_url, destination_filename, already_downloaded_files)


def extract_archive(archive_filename):
    """Unzips zip files and MSIs."""
    _logger.info("Extracting: %r...", archive_filename)
    absolute_path = os.path.abspath(archive_filename)
    targetdir = os.path.splitext(absolute_path)[0]
    subprocess.call(["7z", "x", "-y", absolute_path, "-o" + targetdir])


def extract_archives_in_direcory(path):
    """Recursively extracts all of the zipped/MSI'd files in a provided directory."""
    for root, subdirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            extract_archive(file_path)


def store_pdbs_in_directory(pdb_path, store_path, product, version):
    """Recursively adds all of the pdb files in a provided directory to the symbols store."""
    sym_store = symstore.Store(store_path)
    transaction = sym_store.new_transaction(product, version)
    num_files_stored = 0
    for root, subdirs, files in os.walk(pdb_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Rename the python.pdb to python##.pdb.
            if "core_pdb" in root and file == "python.pdb":
                major, minor, *_ = version.split(".")
                new_file_path = file_path.replace("python.pdb", "python" + major + minor + ".pdb")
                os.rename(file_path, new_file_path)
                file_path = new_file_path
            
            # Add PDB files
            is_compression_supported = symstore.cab.compress is not None
            if file_path.endswith(".pdb"):
                entry = transaction.new_entry(file_path, compress=is_compression_supported)
                transaction.add_entry(entry)
                num_files_stored += 1
    
    if num_files_stored > 0:
        sym_store.commit(transaction)

    
def fetch_and_store_pdbs_for_version(root, product, version, already_downloaded_files):
    temp_folder = version + "-temp/"
    store_folder = "./symbols"
    download_pdbs_for_version(root, version, temp_folder, already_downloaded_files)
    extract_archives_in_direcory(temp_folder)
    store_pdbs_in_directory(temp_folder, store_folder, product, version)
    shutil.rmtree(temp_folder)


def download_pdbs_at_root(root, product, already_downloaded_files):
    available_versions = get_available_python_versions(root)
    _logger.info("Versions available from %s: %r", root, available_versions)

    for version in available_versions:
        fetch_and_store_pdbs_for_version(root, product, version, already_downloaded_files)
    
    
def get_old_stackless_pdb_file_list(root):
    indexhtml = fetch_page(root)
    return re.findall(r"<a\s+href=\"(.*?\bpdb.*?\.zip)\"\s*>", indexhtml)
    
    
def fetch_and_store_old_stackless_pdbs(root, already_downloaded_files):
    archives = get_old_stackless_pdb_file_list(root)
    
    store_folder = "./symbols"    
    for archive in archives:
        temp_folder = archive + "-temp/"
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
    
        source_url = urllib.parse.urljoin(root, archive)
        destination_filename = os.path.join(temp_folder, archive)
        try_download_file(source_url, destination_filename, already_downloaded_files)
        extract_archives_in_direcory(temp_folder)
        store_pdbs_in_directory(temp_folder, store_folder, "StacklessPython", archive)
        shutil.rmtree(temp_folder)
    
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    already_downloaded_files = set(read_downloaded_files_list());
    _logger.info("Files already downloaded: %r", already_downloaded_files)
    
    # Download official Python symbols.
    download_pdbs_at_root("https://www.python.org/ftp/python/", "CPython", already_downloaded_files)
    
    #Download Stackless Python symbols. (3.5+)
    download_pdbs_at_root("http://www.stackless.com/binaries/MSI/", "StacklessPython", already_downloaded_files)
    
    # Download Stackless Python symbols (Older versions.)
    fetch_and_store_old_stackless_pdbs("http://www.stackless.com/binaries/", already_downloaded_files)
    
    save_downloaded_files_list(already_downloaded_files)