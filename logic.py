import data


READER_TYPE_TXT = 11
READER_TYPE_DB = 12
READER_TYPE_API = 13
READER_TYPE_XML = 14

class dataHandler():
    """
    数据对象转换
    """
    def __init__(self, items):
        """
        items: list, 数据项, 可配置
        """
        self.items = items
        self.count = len(self.items)
		
    def handle(self, datas):
        """
        datas： list, 读取到的并已分组的数据
        返回值： 每条数据
        """
        _return = []
        datas.reverse()
        while len(datas) != 0:
            _tmp = []
            for i in range(1, self.count+1):
                try:
                    _tmp.append(datas.pop())
                except IndexError:
                    break
            _return.append(_tmp)
        return _return


class reader():
    """
    根据文件类型读取数据
    """
    def __init__(self, _src, _type):
        self.reader = None
        self.readerType = _type

        if self.readerType == READER_TYPE_TXT:
            self.reader = data.TxtReader(_src)
        elif self.readerType == READER_TYPE_DB:
            self.reader = data.DbReader(_src)
        elif self.readerType == READER_TYPE_API:
            self.reader = data.ApiReader(_src)
        elif self.readerType == READER_TYPE_XML:
            self.reader = data.XmlReader(_src)

        print(self.reader.data)



class _3dlog(dataHandlerCls):
    def handle(self):
        self.startTime = self.datas[1]
        self.index = self.datas[2]
        self.sectionCount = self.datas[3]
        self._type = self.datas[4]
        self.isError = self.datas[5]
        self.endTime = self.datas[6]

class _2dlog(dataHandlerCls):
    def handle(self):
        self.startTime = self.datas[1]
        self.index = self.datas[2]
        self.sectionCount = self.datas[3]
        self._type = self.datas[4]
        self.isError = self.datas[5]
        self.endTime = self.datas[6]


class selfCheckHandler(dataHandlerCls):
    """
    自检日志
    """
    def handle(self):
        self.time = None
        self.failType = None
        self.failDetail = None
        self.failLevel = None
        self.hardErrorCode = None
        self.hardState = None
        self.warningLevel = None

class systemHandler(dataHandlerCls):
    """
    测量系统日志对象
    """
    def handler(self):
        self.time = None
        self.failType = None
        self.failDetail = None
        self.failLevel = None
        self.warningLevel = None



def Start():
    basepath = 'D:/datas/work/limit'
    f1 = 'slant_lms.txt'
    f2 = '2017年03月03日01时45分14秒TmeasuredData_lms.txt'
    f3 = '2D2017年04月26日.log'
    f_selfcheck = '2017年04月26日.log'
    f_3d = '3D2017年04月26日.log'
    # print(sc.failDetail)
    r = reader(os.path.join(basepath, f_3d), READER_TYPE_TXT)