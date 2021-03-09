import os, sys

cur_path = os.path.abspath(os.path.dirname(__file__))
library_path = os.path.join(cur_path, 'lib')
sys.path.insert(1, library_path)
sys.path.insert(1, os.path.join(library_path, "python-uncompyle6"))

from uncompyle6 import main as uncompyle


if __name__ == "__main__":
    apk_out = 'results/eve_xapk/eve-echoes_1.7.4_apk'
    script_npk_out = os.path.join(apk_out, 'assets', 'script_npk')
    filename = os.path.join(script_npk_out, 'patchcore.pyc')

    dirname = os.path.dirname(filename)
    base, ext = os.path.splitext(filename)
    file_base = os.path.basename(filename)
    out_base = base + '.py'
    try:
        uncompyle.main(dirname, None, [file_base], [], outfile=None, source_encoding='utf-8')
    except Exception as e:
        print(f"\n\033[93m{e}\033[0m")