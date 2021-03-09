import os,zlib
from magics import get_magic


def try_ord(x):
    if type(x) is not int:
        return ord(x)
    else:
        return x

def _reverse_string(s):
    l = list(s)
    l = list(map(lambda x: chr(try_ord(x) ^ 154), l[0:128])) + l[128:]
    l.reverse()
    return bytearray(map(lambda x: int(try_ord(x)), l))


def unnpk(filename):
    if not os.path.exists(filename):
        raise Exception(f'{filename} does not exist')
    
    with open(filename, 'rb') as f:
        if get_magic(f.read(12)) != 'nxs':
            raise Exception(f'{filename} is not an NXS file')
        f.seek(0)
        data = f.read()

    asdf_dn = 'j2h56ogodh3se'
    asdf_dt = '=dziaq.'
    asdf_df = '|os=5v7!"-234'
    asdf_tm = asdf_dn * 4 + (asdf_dt + asdf_dn + asdf_df) * 5 + '!' + '#' + asdf_dt * 7 + asdf_df * 2 + '*' + '&' + "'"
    import rotor
    rotor = rotor.newrotor(asdf_tm)
    data = rotor.decrypt(data)
    data = zlib.decompress(data)
    data = _reverse_string(data)

    return data

def unnpk_write(filename, out_name=None):
    data = unnpk(filename)
    out_name = out_name if out_name else filename[:-3] + get_magic(data)

    with open(out_name, 'wb') as f:
        f.write(data)
