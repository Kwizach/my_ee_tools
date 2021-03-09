import os, sys

cur_path = os.path.abspath(os.path.dirname(__file__))
library_path = os.path.join(cur_path, 'lib')
sys.path.insert(1, library_path)
sys.path.insert(1, os.path.join(library_path, "python-uncompyle6"))

import argparse
import time
import zipfile
from pathlib import Path
from multiprocessing import Pool, Value, cpu_count
from unpack import unpack_npk
from magics import get_magic_from_file
from script_redirect import unnpk_write
from pyc_decryptor import PYCEncryptor
from uncompyle6 import main as uncompyle

UNCOMPYLE_FAILED_OUT = 'failed_uncompyle.txt'

def wait_message(msg):
    print(msg.ljust(100), end='', flush=True)

def end_message(msg):
    print(msg)

def print_done_time(start):
    print('\x1b[1;32;40mDone in {:.1f}sec\x1b[0m'.format(time.time()-start))

def check_xapk(xapk_path):
    """
    Check if it is a valid xapk file
    """
    if not os.path.exists(xapk_path):
        print('file does not exist')
        sys.exit(1)
    xapk_name = os.path.basename(xapk_path)
    xapk_basename, xapk_ext = os.path.splitext(xapk_name)
    if xapk_ext != '.xapk' or get_magic_from_file(xapk_path) != 'apk':
        print('files needs to be of xpak format and extension')
        sys.exit(1) 
    return xapk_basename


def build_outdir(outdir, xapk_basename):
    """
    Build output directory and clean it if we can (we do not force)
    """
    extract_xapk = os.path.join(outdir, xapk_basename)
    if os.path.exists(outdir):
        try:
            os.removedirs(outdir)
            os.makedirs(extract_xapk)
        except:
            print(f'{outdir} is not empty')
    else:
        os.makedirs(extract_xapk)

    return extract_xapk


def unzip_apk(apk_path, extract_apk):
    with zipfile.ZipFile(apk_path, 'r') as zip_ref:
        zip_ref.extractall(extract_apk)

def unzip_all_inside(root_dir, extract_obb=True, extract_apk=True):
    """
    Unzip .obb and .apk
    """
    obb_out = None
    apk_out = None
    
    def extract(filename):
        base, ext = os.path.splitext(filename)
        out_path = base # + ext.replace('.','_')
        try:
            os.makedirs(out_path)
            wait_message(f'Unzipping {filename}')
            unzip_apk(filename, out_path)
        except:
            end_message('file already exist')
        else:
            end_message('OK')
        return out_path

    if extract_obb:
        for obb_filename in Path(root_dir).rglob("*.obb"):
            obb_out = extract(str(obb_filename))
    
    if extract_apk:
        for apk_filename in Path(root_dir).rglob("*.apk"):
            apk_out = extract(str(apk_filename))

    return obb_out, apk_out


def unnpk_all_nxs(filename):
    with counter.get_lock():
        counter.value += 1

    print("\r\x1b[2K{:{}}/{} > {}".format(counter.value, 5, nb_files, filename[root_len:]), end='')
    unnpk_write(filename)

def uncrypt_all_cpyc(filename):
    with counter.get_lock():
        counter.value += 1

    print("\r\x1b[2K{:{}}/{} > {}".format(counter.value, 5, nb_files, filename[root_len:]), end='')
    encryptor.decrypt_file(filename)

def uncompyle_all_pyc(filename):
    with counter.get_lock():
        counter.value += 1

    if failed.value:
        print("\r\x1b[2K{:{}}/{} | \x1b[91mFailed: {}\x1b[0m > {}".format(counter.value, 5, nb_files, failed.value, filename[root_len:]), end='')
    else:
        print("\r\x1b[2K{:{}}/{} > {}".format(counter.value, 5, nb_files, filename[root_len:]), end='')
        
    dirname = os.path.dirname(filename)
    base, ext = os.path.splitext(filename)
    file_base = os.path.basename(filename)
    out_base = base + '.py'
    try:
        uncompyle.main(dirname, None, [file_base], [], outfile=out_base, source_encoding='utf-8')
    except Exception as e:
        failed_file = os.path.join(filename[:root_len], UNCOMPYLE_FAILED_OUT)
        with open(failed_file, 'a') as f:
            f.write(filename[root_len:]+"\n")
        with failed.get_lock():
            failed.value += 1


def init(co, n_f, r_l, enc, fa):
    """
    Share global and lock with workers
    """
    global counter, nb_files, root_len, encryptor, failed
    counter = co
    nb_files = n_f
    root_len = r_l
    encryptor = enc
    failed = fa


def main():
    parser = argparse.ArgumentParser(description='Eve Tools')
    parser.add_argument('xapk_path', type=str, action='store', help="npk file")
    parser.add_argument('out_dir', type=str, action='store', help="output directory")
    args = parser.parse_args()

    xapk_path = args.xapk_path
    out_dir = args.out_dir

    xapk_basename = check_xapk(xapk_path)

    extract_xapk = build_outdir(out_dir, xapk_basename)
    
    wait_message(f'Unzipping {xapk_basename}.xpak')
    unzip_apk(xapk_path, extract_xapk)
    end_message('OK')

    obb_out, apk_out = unzip_all_inside(extract_xapk, extract_obb=True)

    script_npk = os.path.join(apk_out, 'assets', 'script.npk')
    script_npk_out = os.path.join(apk_out, 'assets', 'script')

    sys.stdout.write("\x1b[?25l")
    print('\x1b[1;36;40m*****  npk to nxs (script.npk) *****\x1b[0m')
    start = time.time()
    unpack_npk([script_npk], script_npk_out)
    print_done_time(start)

    print('\x1b[1;36;40m*****  extract npks (res*.npk) *****\x1b[0m')
    start = time.time()
    all_res_npk = list(map(lambda x: str(x), Path(obb_out).rglob("*.npk")))
    all_res_npk_out = os.path.join(obb_out, 'res_npk')
    unpack_npk(all_res_npk, all_res_npk_out)
    print_done_time(start)

    workflow = [
        {
            'msg': '***** nxs to cpyc *****', 
            'func': unnpk_all_nxs, 
            'ext': '.nxs'
        },
        {
            'msg': '***** cpyc to pyc *****', 
            'func': uncrypt_all_cpyc, 
            'ext': '.cpyc'
        },
        {
            'msg': '*****  pyc to py  *****', 
            'func': uncompyle_all_pyc, 
            'ext': '.pyc'
        }
    ]

    global counter, root_len, encryptor
    root_len = len(script_npk_out)+1
    encryptor = PYCEncryptor()
    for task in workflow:
        counter = Value('i', 0)
        failed = Value('i', 0)
        nb_files = len(list(Path(script_npk_out).rglob("*"+task['ext'])))

        print("\x1b[1;36;40m"+task['msg']+"\x1b[0m")

        initargs = (counter, nb_files, root_len, encryptor, failed, )
        start = time.time()
        with Pool(cpu_count(), initializer=init, initargs=initargs) as pool:
            pool.map_async(task['func'], map(lambda x: str(x), Path(script_npk_out).rglob("*"+task['ext']))).get(99999)
        
        print()
        print_done_time(start)
        if failed.value:
            print('\x1b[0;33;40m{} failed, wrote in {}\x1b[0m'.format(failed.value, os.path.join(script_npk_out, UNCOMPYLE_FAILED_OUT)))

    sys.stdout.write("\x1b[?25h")

def patch():
    doc_path = os.path.abspath(os.path.join(script_npk_out, 'robot', 'doc'))


if __name__ == "__main__":
    main()