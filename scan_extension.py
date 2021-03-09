import os
import argparse
import json
from lib.magics import get_magic_from_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scan files')
    parser.add_argument('root_directory', type=str, action='store', help="root directory")
    args = parser.parse_args()

    all_files = { 'unknown': 0 }
    for root, dirs, files in os.walk(args.root_directory):
        for name in files:
            filename = os.path.join(root, name)
            magic = get_magic_from_file(filename)
            if magic != 'unknown':
                print(f' {magic} '.ljust(6) + f'- {filename}')
                if magic in all_files:
                    all_files[magic] += 1
                else:
                    all_files[magic] = 1
            else:
                all_files['unknown'] += 1
    
    print(json.dumps(all_files, indent=4, sort_keys=True))