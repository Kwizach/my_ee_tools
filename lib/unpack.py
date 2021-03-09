import os, struct, math, re, zlib
from lz4.block import decompress as lz4_decompress, LZ4BlockError
from magics import get_magic
from multiprocessing import Pool, Lock, cpu_count, get_context

def readuint64(f):
    return struct.unpack_from("<Q",f.read(8))[0]

def readuint32(f):
    return struct.unpack('I', f.read(4))[0]

def readuint16(f):
    return struct.unpack('H', f.read(2))[0]

def readuint8(f):
    return struct.unpack('B', f.read(1))[0]


SCRIPT_LIST_HASH = 0x4557903497D4CDAA
RES_LIST_HASH = 0xD4A17339F75381FD
MMH_TOP_SEED = 0x9747B28C
MMH_BOTTOM_SEED = 0xC82B7479

path_hash_map = {}

class NPKReader(object):
    """
    Class to read NPK content
    """

    def __init__(self, filename, find_list=True, position=0):
        """
        Start by reading the header and find the filelist.txt to create path_hash_map
        """
        self.position = position
        self.filename = filename
        self.basename = os.path.basename(self.filename)
        
        if not os.path.exists(filename):
            raise Exception(f'No such file {filename}')
        
        if not self._is_NPK():
            raise Exception('Not an NXPK file')
        
        self.npk_map = []
        self.unknown_extract = 0

        self.read_header()
        self.read_map()
        if find_list:
            self.find_filelist()
        
        
    def _is_NPK(self):
        """
        Make sure we have a NPK file
        """
        with open(self.filename, 'rb') as f:
            data = f.read(4)
            if data != b'NXPK':
                return False
        return True
    
    def read_header(self):
        """
        Read NPK header
        """
        with open(self.filename, 'rb') as f:
            self.npk_size = f.seek(0, 2)
            f.seek(0x4)
            self.nb_files = readuint32(f)                   # 0x4
            self.large_file_index_offset = readuint32(f)    # 0x8
            var2 = readuint32(f)                            # 0xc
            var3 = readuint32(f)                            # 0x10
            self.map_offset = readuint32(f)                 # 0x14

            info_size = (self.npk_size-self.map_offset)/self.nb_files
            if info_size != int(info_size):
                raise Exception(f'info_size: {info_size}')
            self.info_size = int(info_size)

            if info_size == 0x28:
                self.version = 2
            elif info_size == 0x1C:
                self.version = 1
            else:
                raise Exception(f'Unkown version -> info_size: {info_size}')


    def read_map(self):
        """
        Read the map of the NPK and yield every single file information in the NPK
        for further extract or read
        """
        with open(self.filename, 'rb') as f:
            for file_num in range(self.nb_files):
                if self.version == 2:
                    self._read_map_v2(f, file_num)
                else:
                    self._read_map_v1(f, file_num)


    def _read_map_v1(self, f, file_num):
        """
        Version 1 format (28bytes)
        Read fields and return them
        """
        name_hash = readuint32()
        file_offset = readuint32()
        compressed_size = readuint32()
        uncompressed_size = readuint32()

        field_16 = readuint64()

        compress_type = readuint16()
        encrypt_type = readuint8()
        large_file_offset = readuint8()
        
        self.npk_map.append(
            (name_hash, file_offset, compressed_size, uncompressed_size,
                field_16, compress_type, encrypt_type, large_file_offset)
        )

    def _read_map_v2(self, f, file_num):
        """
        Version 2 format (40bytes)
        Read fields and return them
        """
        f.seek(self.map_offset + file_num * self.info_size)

        name_hash = readuint64(f)
        file_offset = readuint32(f)
        compressed_size = readuint32(f)
        uncompressed_size = readuint32(f)
        
        field_20 = readuint32(f)
        field_24 = readuint64(f)
        field_32 = readuint8(f)
        field_33 = readuint8(f)
        field_34 = readuint8(f)
        field_35 = readuint8(f)

        compress_type = readuint16(f)
        encrypt_type  = readuint8(f)
        large_file_offset = readuint8(f)

        self.npk_map.append(
            (name_hash, file_offset, compressed_size, uncompressed_size,
                field_20, field_24, field_32, field_33, field_34, field_35,
                compress_type, encrypt_type, large_file_offset)
        )
    

    def find_filelist(self):
        """
        Find the filelist.txt to create path_hash_map
        """
        # This is the hash for script.npk
        files = list(filter(lambda x: x[0] == SCRIPT_LIST_HASH, self.npk_map))
        if len(files):
            file_list = files[0]
            self.create_path_hash_mapping_for_script_npk(file_list[1], file_list[2], file_list[3])
        else:
            # This is the hash for res0.npk
            files = list(filter(lambda x: x[0] == RES_LIST_HASH, self.npk_map))
            if len(files):
                file_list = files[0]
                self.create_path_hash_mapping_for_res_npk(file_list[1], file_list[2], file_list[3])


    def create_path_hash_mapping_for_script_npk(self, f_o, c_s, u_s):
        """
        Map file paths found in filelist with their hash
        Store them in self.path_hash_map
        """
        import mmh3
        global path_hash_map

        with open(self.filename, 'rb') as f:
            f.seek(f_o)
            data = f.read(c_s)

        try:
            data = lz4_decompress(data, uncompressed_size=u_s)
        except LZ4BlockError as e:
            print(f'Error: {e}')

        files = data.decode('utf-8').split('\n')
        for file_str in files:
            if file_str != '':
                path_split = file_str.split('/')
                file_path = os.path.join(*path_split)
                file_str = re.sub('^lib\/', '', file_str)
                file_str = re.sub('^engine\/common\/', '', file_str)
                file_str = re.sub('^engine\/', '', file_str)
                file_str = file_str.replace('/', '\\')
                top =  mmh3.hash(file_str, signed=False, seed=MMH_TOP_SEED)
                bottom = mmh3.hash(file_str, signed=False, seed=MMH_BOTTOM_SEED)
                path_hash = bottom | top << 0x20
                path_hash_map[path_hash] = file_path


    def create_path_hash_mapping_for_res_npk(self, f_o, c_s, u_s):
        import mmh3
        global path_hash_map

        with open(self.filename, 'rb') as f:
            f.seek(f_o)
            data = f.read(c_s)

        try:
            data = zlib.decompress(lz4_decompress(data, uncompressed_size=u_s))
        except LZ4BlockError as e:
            print(f'Error: {e}')
        except Exception as e:
            print(e)

        files = data.decode('utf-8').split('\n')
        for file_str in files:
            parser = re.search("^.*?(\d+).*\s+(.*)$", file_str)
            name_hash = int(parser.group(1))
            filename = str(parser.group(2))
            path_hash_map[name_hash] = filename


    def extract(self, output_path):
        """
        Extract a file from the NPK
        """
        if self.version == 2:
            file_num = 0
            for file_info in self.npk_map:
                n_h, f_o, c_s, u_s, c_t, e_t, l_f_o = (file_info[0], file_info[1], file_info[2], file_info[3], file_info[10], file_info[11], file_info[12])
                file_num += 1
                self.extract_v2(output_path, file_num, n_h, f_o, c_s, u_s, c_t, e_t, l_f_o)
        else:
            for file_info in self.npk_map:
                self.extract_v1(output_path, *file_info)
        # print()
    
    def extract_v1(self, output_path, args):
        """
        NPK v1 extraction
        """
        pass

    def extract_v2(self, output_path, file_num, n_h, f_o, c_s, u_s, c_t, e_t, l_f_o):
        """
        NPK v2 extraction
        """
        offset = f_o if f_o else l_f_o << 20
        name = hex(n_h).replace('0x', '').upper()
        with open(self.filename, 'rb') as f:
            f.seek(offset)
            data = f.read(c_s)
        
        # encryption is not yet supported
        if c_t == 1:
            print('Zlib')
        elif c_t == 2:
            try:
                data = lz4_decompress(data, uncompressed_size=u_s)
            except LZ4BlockError as e:
                print(f'Error: {e}')
        
        try:
            file_path = path_hash_map[n_h]
        except:
            if n_h == SCRIPT_LIST_HASH:
                file_path = 'tmpvrmBoP.lst'
            elif n_h == RES_LIST_HASH:
                file_path = 'filelist.txt'
                data = zlib.decompress(data)
            else:
                file_path = '_unknown_'+str(n_h)
                self.unknown_extract += 1

        ext_from_magic = get_magic(data)
        if ext_from_magic != 'unknown' and ext_from_magic != 'none':
            basename, ext = os.path.splitext(file_path)
            file_path = basename +'.'+ get_magic(data)
    
        lock.acquire()
        move = nb_readers - self.position
        print(f"\x1b[{move}A", end='')
        if self.unknown_extract:
            print("\x1b[2K\x1b[1;33;40m{:<10} >>\x1b[0m {:5}/{:<5} | \x1b[0;30;43munknown: {}\x1b[0m > {}".format(self.basename, file_num, self.nb_files, self.unknown_extract, file_path), end='')
        else:
            print("\r\x1b[2K\x1b[1;33;40m{:<10} >>\x1b[0m {:5}/{:<5} > {}".format(self.basename, file_num, self.nb_files, file_path), end='')
        print(f"\r\x1b[{move}B", end='')
        lock.release()

        file_path = os.path.join(output_path, file_path)
        self.write_output(file_path, data)
        
        
    def write_output(self, file_path, data):
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        
        with open(file_path, 'wb') as f:
            f.write(data)


    def pretty_print_header(self):
        """
        pretty print the header
        """
        print('-------- NPK HEADER --------')
        print(f' npk_size:   {self.npk_size}')
        print(f' nb_files:   {self.nb_files}')
        print(f' map_offset: {self.map_offset}')
        print(f' info_size:  {self.info_size}')
        print(f' version:    {self.version}')
        print(f' large_file_index_offset: {self.large_file_index_offset}')
        print('----------------------------')
    
    
    def pretty_csv_map(self):
        """
        csv export the map of the NPK
        """
        print(f'file_num,name_hash,file_offset,compressed_size,uncompressed_size,field_20,field_24,field_32,field_33,field_34,field_35,compress_type,encrypt_type,large_file_offset')
        file_num=0
        for line in self.npk_map:
            name_hash, file_offset, compressed_size, uncompressed_size, \
                field_20, field_24, field_32, field_33, field_34, field_35, \
                compress_type, encrypt_type, large_file_offset = line
            print(f'{file_num},{name_hash},{file_offset},{compressed_size},{uncompressed_size},{field_20},{field_24},{field_32},{field_33},{field_34},{field_35},{compress_type},{encrypt_type},{large_file_offset}')
            file_num += 1



def call_extract(npk_reader, output_path):
    npk_reader.extract(output_path)

def init(l, p_h_m, n_r):
    global lock, path_hash_map, nb_readers
    lock = l 
    path_hash_map = p_h_m
    nb_readers = n_r

def unpack_npk(filenames, output_path=None):
    """
    Unpack the NPK 
    """
    if output_path is None:
        output_path = os.path.dirname(os.path.realpath(filenames[0]))
        npk_basename, _ = os.path.splitext(os.path.basename(filenames[0]))
        output_path = os.path.join(output_path, npk_basename)

    if os.path.exists(output_path):
        try:
            os.removedirs(output_path)
            os.makedirs(output_path)
        except:
            print(f'{output_path} is not empty, leaving it as is')
    else:
        os.makedirs(output_path)

    global lock, path_hash_map, nb_readers
    lock = Lock()
    path_hash_map = {}
    nb_readers = len(filenames)

    npk_readers = []
    search_filelist = True
    position = 0
    for filename in filenames:
        npk_reader = NPKReader(filename, search_filelist, position)
        npk_readers.append(npk_reader)
        if len(path_hash_map):
            search_filelist = False
        print("\x1b[2K\x1b[1;33;40m{}\x1b[0m".format(os.path.basename(filename)))
        position += 1 
    
    initargs = (lock, path_hash_map, nb_readers)
    with get_context("spawn").Pool(cpu_count(), initializer=init, initargs=initargs) as pool:
        pool.starmap(call_extract, [(npk_reader, output_path) for npk_reader in npk_readers])


def inspect_npk(filenames):
    """
    NPK inspector
    Print Header and Map
    """
    npk_reader = NPKReader(filename)
    npk_reader.pretty_print_header()
    npk_reader.pretty_csv_map()


if __name__ == "__main__":
    pass