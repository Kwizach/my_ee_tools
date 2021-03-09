def get_magic_from_file(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    return  get_magic(data)

def get_magic(data):
    if len(data) == 0:
        return 'none'
    if data[:4] == b'PK\x03\x04':
        return 'apk'
    if data[:4] == b'EXPK':
        return 'epk'
    if data[:4] == b'NXPK':
        return 'npk'
    elif data[:2] == b'\x1d\x04':
        return 'nxs'
    elif data[:9] == b'c\x00\x00\x00\x00\x00\x00\x00\x00':
        return 'cpyc'
    elif data[:4] == b'\x03\xf3\r\n':
        return 'pyc'
    elif data[:12] == b'CocosStudio-UI':
        return 'coc'
    elif data[:3] == b'hit':
        return 'hit'
    elif data[:3] == b'PKM':
        return 'pkm'
    elif data[:3] == b'PVR':
        return 'pvr'
    elif data[:3] == b'DDS':
        return 'dds'
    elif data[1:4] == b'KTX':
        return 'ktx'
    elif data[1:4] == b'PNG':
        return 'png'
    elif data[:4] == bytes([0x34, 0x80, 0xC8, 0xBB]):
        return 'mesh'
    elif data[:4] == bytes([0x14, 0x00, 0x00, 0x00]):
        return 'type1'
    elif data[:4] == bytes([0x04, 0x00, 0x00, 0x00]):
        return 'type2'
    elif data[:4] == bytes([0x00, 0x01, 0x00, 0x00]):
        return 'type3'
    elif data[:4] == b'VANT':
        return 'vant'
    elif data[:4] == b'MDMP':
        return 'mdmp'
    elif data[:4] == b'RGIS':
        return 'rgis'
    elif data[:4] == b'NTRK':
        return 'ntrk'
    elif data[:4] == b'RIFF':
        return 'riff'
    elif data[:4] == b'BKHD':
        return 'bnk'
    return 'unknown'
