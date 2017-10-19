import os
import os.path
import datetime
import time

from ctypes import *
from xml.etree import ElementTree as ET
import pymssql



FILE_TYPE_LOG = 1
FILE_TYPE_INDEX = 2
FILE_TYPE_LADER = 3
FILE_TYPE_SLANT = 4
FILE_TYPE_MEASURE = 5
FILE_TYPE_JPG = 6

class InputData(Structure):
    _fields_ = [('m_index', c_int),  
                ('m_path', c_char_p),
                ('m_trtype', c_char_p)
                ]

class OutputData(Structure):
    _fields_ = [
        ('m_TrPacksCount', c_int),
        ('m_TrHeightData', c_char_p),
        ('m_TrLeftWidthData', c_char_p),
        ('m_TrRightWidthData', c_char_p)
    ]


class dataReaderCls(): 
    def __init__(self, src):
        self.src = src
        self.data = []
        try:
            self.begin()
            self.read()
        except Exception as e:
            print(e)
        finally:
            self.end()
            print('读取操作结束!')

    def begin(self):
        pass

    def read(self):
        pass

    def end(self):
        pass


class DbReader(dataReaderCls):
    """
    self.src =
    [
        host,
        user,
        password,
        database
    ]
    """
    def begin(self):
        self.cur = None
        self.conn = pymssql.connect(host=self.src[0], user=self.src[1], password=self.src[2], database=self.src[3])
        self.cur = self.conn.cursor()
        if self.cur is None:
            raise EnvironmentError

    def read(self):
        print('read')

    def end(self):
        print('end')
        self.conn.close()

class ApiReader(dataReaderCls):
    def begin(self):
        self.src = cdll.LoadLibrary('TrStandardDataCheck.dll')
        if self.src is None:
            raise FileNotFoundError

    def read(self):
        _in = InputData()
        self.src.GetMeasuredData.restype = POINTER(OutputData)
        self.src.GetMeasuredData.argtypes = [POINTER(InputData)]
        self.data = self.src.GetMeasuredData(_in)
        # print(self.data.contents.m_TrPacksCount)
        # print(self.data.contents.m_TrHeightData)
        # print(self.data.contents.m_TrLeftWidthData)
        # print(self.data.contents.m_TrRightWidthData)

class XmlReader(dataReaderCls):
    def begin(self):
        self.tree = ET.parse(self.src)
        if self.tree is None:
            raise FileNotFoundError
        self.xRightInput_1 = './/caltime[@no="1"]/right_radar/input_par'
        self.xRightCali_1 = './/caltime[@no="1"]/right_radar/cali_par'
        self.xLeftInput_1 = './/caltime[@no="1"]/left_radar/input_par'
        self.xLeftCali_1 = './/caltime[@no="1"]/left_radar/cali_par'
        self.xInput_2 = './/caltime[@no="2"]/input_par'
        self.xCali_2 = './/caltime[@no="2"]/cali_par'
    
    def read(self):
        """
        self.data = [
            # 一次标定
            [
                左雷达安装位置（radarheight，road_radar_dis），
                左实际测量位置（road_radar_dis， radarheight）,
                右雷达安装位置（radarheight，road_radar_dis），
                右实际测量位置（road_radar_dis， radarheight）
            ]
            # 二次标定
            [
                标定板尺寸（height， width），
                实际测量尺寸（大高，小高，大长，小长，均高，均长）
            ]
        ]
        """
        root = self.tree.getroot()
        _1time = []
        xLeftInput_1 = root.find(self.xLeftInput_1)
        _1time.append((xLeftInput_1.get('radarheight'), xLeftInput_1.get('road_radar_dis')))
        xLeftCali_1 = root.find(self.xLeftCali_1)
        _1time.append((xLeftCali_1.get('road_radar_dis'), xLeftCali_1.get('radarheight')))
        xRightInput_1 = root.find(self.xRightInput_1)
        _1time.append((xRightInput_1.get('radarheight'), xRightInput_1.get('road_radar_dis')))
        xRightCali_1 = root.find(self.xRightCali_1)
        _1time.append((xRightCali_1.get('road_radar_dis'), xRightCali_1.get('radarheight')))
        self.data.append(_1time)
        
        _2time = []
        xInput_2 = root.find(self.xInput_2)
        _2time.append((xInput_2.get('height'), xInput_2.get('width')))
        xCali_2 = root.find(self.xCali_2)
        _2time.append(
            (
                xCali_2.get('max_height'),
                xCali_2.get('min_height'),
                xCali_2.get('max_width'),
                xCali_2.get('min_width'),
                xCali_2.get('avg_height'),
                xCali_2.get('avg_width')
                ))
        self.data.append(_2time)
        # print(self.data)


class TxtReader(dataReaderCls):
    """
    self.src: 文本文件全路径
    """
    def begin(self):
        if not os.path.exists(self.src): 
            raise FileNotFoundError

    def read(self):
        def _filter(x):
            return x != '' and x != '.'
        lines = []
        with open(self.src, 'r') as fo:
            while True:
                _tmp = fo.readlines(5000)
                if not _tmp:
                    break
                else:
                    lines.extend(_tmp)
            self.data = list(filter(_filter, self._format(lines)))
        # print(self.data)

    def _format(self, data):
        _tmp = ''.join(data)
        while ' ' in _tmp:
            _tmp = _tmp.replace(' ', '')
        _tmp = _tmp.replace('\t', '$$')
        _tmp = _tmp.replace('][', '$$')
        _tmp = _tmp.replace('\n', '$$')
        _tmp = _tmp.replace(']', '')
        _tmp = _tmp.replace('[', '')
        _tmp = _tmp.replace(',', '')
        return _tmp.split('$$')


class dataHandle():
    """
    数据对象转换
    """
    def __init__(self, items, datas, _filter=None):
        """
        items: list, 数据项, 可配置
        """
        # print(datas)
        self.items = items
        self.datas = dict()
        self.handle(datas)
		
    def handle(self, datas):
        """
        datas： list, 读取到的并已分组的数据
        返回值： 每条数据
        """
        _return = []
        datas.reverse()
        while len(datas) != 0:
            _tmp = []
            for i in range(1, len(self.items)+1):
                try:
                    _tmp.append(datas.pop())
                except IndexError:
                    break
            _return.append(_tmp)
       
        if _return != []:
            for l in _return:
                print('l >', l)
                for item in self.items:
                    self.datas[item] = list()
                for item in self.items:
                    self.datas[item].append(l[self.items.index(item)])

    def format(self):
        pass


READER_TYPE_TXT = 11
READER_TYPE_DB = 12
READER_TYPE_API = 13
READER_TYPE_XML = 14

class reader():
    """
    根据文件类型选择操作类
    """
    def __init__(self, _src, _type):
        self.reader = None
        self.readerType = _type

        if self.readerType == READER_TYPE_TXT:
            self.reader = TxtReader(_src)
        elif self.readerType == READER_TYPE_DB:
            self.reader = DbReader(_src)
        elif self.readerType == READER_TYPE_API:
            self.reader = ApiReader(_src)
        elif self.readerType == READER_TYPE_XML:
            self.reader = XmlReader(_src)
    
    def _get_datetime(self, _time):
        _return = None
        if isinstance(_time, datetime.datetime):
            _year = _time.strftime('%Y')
            _month = _time.strftime('%m')
            _day = _time.strftime('%d')
            _hour = _time.strftime('%H')
            _minute = _time.strftime('%M')
            _second = _time.strftime('%S')
            _return = '%s年%s月%s日%s时%s分%s秒' % (_year, _month, _day, _hour, _minute, _second)
        return _return

class logic:
    def __init__(self):
        self.fields = [
            'checkEquipmentStatus',
            'checkDataQuality',
            'validationMeasurePerformance'
        ]

    def checkEquipmentStatus(self):
        pass

    def checkDataQuality(self):
        pass

    def validationMeasurePerformance(self):
        pass

    



def Start():
    db_conn = [
        '172.1.10.136',
        'sa',
        'toecylq',
        'master'
    ]
    f_2d_log = 'D:/datas/work/limit/日志/成像日志/2D/2D2017年04月26日.log'
    f_3d_log = 'D:/datas/work/limit/日志/成像日志/3D/3D2017年04月26日.log'
    f_sys_log = 'D:/datas/work/limit/日志/系统日志/2017年04月26日.log'
    f_check_log = 'D:/datas/work/limit/日志/自检日志/2017年04月26日.log'
    f_index = 'D:/datas/work/limit/输出/雷达输出/数据/20170303014514/index.txt'
    f_measure = 'D:/datas/work/limit/输出/雷达输出/数据/20170303014514/2017年03月03日01时45分14秒TmeasuredData_lms.txt'
    f_slant = 'D:/datas/work/limit/输出/雷达输出/数据/20170303014514/2017年03月03日01时45分14秒slant_lms.txt'
    f_2d3ddata_path = 'D:/datas/work/limit/输出/雷达输出/数据/20170303014514'
    f_2ddata_file = '2017年03月03日01时45分14秒2DTmeasuredData_1_lms.txt'
    f_3ddata_file = '2017年03月03日01时45分14秒3DTmeasuredData_1_lms.txt'
    xml_lidarcal = 'D:/codes/p/OverLimit/LidarCal.xml'
    # f_index = 'D:/datas/work/limit/输出/雷达输出/数据/20170303014514'
    
    # rdb = reader(db_conn, READER_TYPE_DB)
    _lst = [
        f_2d_log,
        f_3d_log,
        f_sys_log,
        f_check_log,
        f_index,
        f_measure,
        f_slant,
        os.path.join(f_2d3ddata_path, f_2ddata_file),
        os.path.join(f_2d3ddata_path, f_3ddata_file)
    ]
    datas = []
    r = reader(xml_lidarcal, READER_TYPE_XML)
    # _items = [
    #     'A',
    #     'B',
    #     'C'
    # ]
    # h = dataHandle(_items, r.reader.data)
    # print(h.datas)



if __name__ == '__main__':
    Start()
