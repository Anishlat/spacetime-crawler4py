from pathlib import Path


def mkdir(path: Path) -> None:
    folder_path = Path(path)
    folder_path.mkdir(parents=True, exist_ok=True) # Make folder if it doesn't exist

def create_base_files():
    mkdir("/data")
    mkdir("/data/urls.json")
    mkdir("/data/tokenFrequency.json")
    mkdir("/data/tokenFrequencySite.json")
