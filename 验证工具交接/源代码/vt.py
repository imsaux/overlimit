# encoding=utf-8
# from multiprocessing import Process, Pool, managers, Manager, Queue, Lock, cpu_count, context
# from multiprocessing.spawn import freeze_support
# from ctypes import *
# from xml.etree import ElementTree as ET
# from PySide.QtCore import *
# from PySide.QtGui import *
import os
import sys
import os.path
import datetime
import time
import asyncio
import threading
import multiprocessing
import ctypes
import configparser
import logging
import PySide.QtCore
import PySide.QtGui
import codecs

_vt_conf = None

FILE_TYPE_LOG = 1
FILE_TYPE_INDEX = 2
FILE_TYPE_LADER = 3
FILE_TYPE_SLANT = 4
FILE_TYPE_MEASURE = 5
FILE_TYPE_JPG = 6

itemsSettting = {
    '目录':[
        '日志根目录',
        '数据根目录',
    ],
    '数据库':[
        '服务器',
        '登录名',
        '密码',
        '数据库'
    ],
    '超限报警车阈值':[
        '敞车',
        '棚车'
    ],
    '超限报警车3D图':[
        '时限'
    ],
    '标定误差验证':[
        '最大误差阈值',
        '最小误差阈值',
        '平均误差阈值'
    ]
}


itemsMainwindow = {
    '设备状态检查': [
        '串口运行状态检查',
        '雷达网络运行状态检查',
        '测量系统运行状态检查'
    ],
    '数据质量检查':[
        '标定完整性检查',
        '测量数据完整性检查',
        '传输数据完整性检查',
        '车号识别率'
    ],
    '测量性能验证':[
        '一次标定误差验证',
        '二次标定误差验证',
        '标准车型测量误差验证',
        '超限报警车型验证',
        '超限报警车3D图性能验证'
    ]
}

def _gettime(_time=None, _type='socket'):
    """
    获取特定格式的日期时间字符串
    """
    t = None
    if _time is None:
        t = datetime.datetime.now()
    elif isinstance(_time, datetime.datetime):
        t = _time
    else:
        return None

    if _type == 'socket':
        return t.strftime("%Y-%m-%d %H:%M:%S")
    elif _type == 'file':
        return t.strftime("%Y%m%d")
    else:
        return None
    
"""
logging模块初始化
"""
logging.basicConfig(
    level=10,
    filename='%s.log' % (_gettime(datetime.datetime.now(), _type='file')),
    format='[time]%(asctime)-15s[time] %(filename)s[line:%(lineno)d] %(levelname)s >>> %(message)s',
    datefmt='[%Y-%m-%d %H:%M:%S]',
    filemode='a'
)  # 全局日志模块 



class dataReaderCls(): 
    def __init__(self, src):
        self.src = src
        self.data = []
        self.handle = None
        try:
            self.begin()
            self.read()
        except Exception as e:
            logging.error(e)
        finally:
            self.end()
            logging.debug('数据读取完毕')

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
        import pymssql
        self.cur = None
        #print(self.src)
        self.conn = pymssql.connect(host=self.src[0], user=self.src[1], password=self.src[2], database=self.src[3])
        self.cur = self.conn.cursor()
        if self.cur is None:
            raise EnvironmentError

    def read(self):
        self.cur.execute(self.src[4])
        self.data = self.cur.fetchall()

    def end(self):
        self.conn.close()


class ApiReader(dataReaderCls):


    class InputData(ctypes.Structure):
        _fields_ = [('m_index', ctypes.c_int),
                    ('m_path', ctypes.c_char_p),
                    ('m_trtype', ctypes.c_char_p)
                    ]

    class OutputData(ctypes.Structure):
        _fields_ = [
            ('m_TrPacksCount', ctypes.c_int),
            ('m_TrHeightData', ctypes.c_char_p),
            ('m_TrLeftWidthData', ctypes.c_char_p),
            ('m_TrRightWidthData', ctypes.c_char_p)
        ]

    def begin(self):
        dllpath = 'TrStandardDataCheck.dll'
        logging.debug('dll path -> ' + repr(dllpath))
        logging.debug('dll path -> ' + repr(os.path.exists(dllpath)))
        if os.path.exists(dllpath):
            self.handle = ctypes.cdll.LoadLibrary(dllpath)
        if self.handle is None:
            logging.error('> dll handle is NONE')

    def read(self):
        # 传入的self.src是一个列表，含有调用接口的全部信息
        _in = ApiReader.InputData()
        if self.src is not None:
            _in.m_index = self.src[0]
            _in.m_path = self.src[1]
            _in.m_trtype = self.src[2]
            self.handle.GetMeasuredData.restype = ctypes.POINTER(ApiReader.OutputData)
            self.handle.GetMeasuredData.argtypes = [ctypes.POINTER(ApiReader.InputData)]
            self.data = self.handle.GetMeasuredData(_in)
        else:
            self.data = None

class XmlReader(dataReaderCls):
    def begin(self):
        import xml.etree.ElementTree as ET
        self.tree = ET.parse(self.src)
        if self.tree is None:
            raise FileNotFoundError

    def read(self):
        root = self.tree.getroot()

        for line in root.findall('./'):
            _name = line.get('name')
            _line_status = line.get('status')
            _status1 = line.find(".caltime[@no='1']").get('status')
            _left1 = (
                (
                    line.find(".caltime[@no='1']/left_radar/input_par").get('road_radar_dis'),
                    line.find(".caltime[@no='1']/left_radar/cali_par").get('road_radar_dis')
                ),
                (
                    line.find(".caltime[@no='1']/left_radar/input_par").get('radarheight'),
                    line.find(".caltime[@no='1']/left_radar/cali_par").get('radarheight')
                )
            )
            _right1 = (
                (
                    line.find(".caltime[@no='1']/right_radar/input_par").get('road_radar_dis'),
                    line.find(".caltime[@no='1']/right_radar/cali_par").get('road_radar_dis')
                ),
                (
                    line.find(".caltime[@no='1']/right_radar/input_par").get('radarheight'),
                    line.find(".caltime[@no='1']/right_radar/cali_par").get('radarheight')
                )
            )
            _status2 = line.find(".caltime[@no='2']").get('status')
            _left2 = (
                (
                    line.find(".caltime[@no='2']/left_radar/input_par").get('width'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('avg_width'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('min_width'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('max_width')
                ),
                (
                    line.find(".caltime[@no='2']/left_radar/input_par").get('height'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('avg_height'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('min_height'),
                    line.find(".caltime[@no='2']/left_radar/cali_par").get('max_height')
                )
            )
            _right2 = (
                (
                    line.find(".caltime[@no='2']/right_radar/input_par").get('width'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('avg_width'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('min_width'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('max_width')
                ),
                (
                    line.find(".caltime[@no='2']/right_radar/input_par").get('height'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('avg_height'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('min_height'),
                    line.find(".caltime[@no='2']/right_radar/cali_par").get('max_height')
                )
            )
            
            self.data.append(((_status1, _status2), (_left1, _right1, _left2, _right2), (_name, _line_status)))
        


class TxtReader(dataReaderCls):
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
            # self.data = self._format(lines)


    def _format(self, data):
        _tmp = ''.join(data)
        _tmp = _tmp.replace('\t', '$$')
        _tmp = _tmp.replace('][', '$$')
        _tmp = _tmp.replace('\n', '$$')
        _tmp = _tmp.replace(']', '')
        _tmp = _tmp.replace('[', '')
        _tmp = _tmp.replace(',', '')
        _tmp = _tmp.replace('.', '')
        return _tmp.split('$$')


class dataHandle():
    def __init__(self, items, datas):
        # print(datas)
        self.items = items
        self.datas = dict()
        self.handle(datas)
		
    def handle(self, datas):
        _return = []
        datas.reverse()
        _tmp = []
        while len(datas) != 0:
            for i in range(1, len(self.items)+1):
                try:
                    _v = datas.pop()
                    _tmp.append(_v)
                except IndexError:
                    break
            _return.append(_tmp)
        if _return != []:
            for item in self.items:
                self.datas[item] = list()
            for l in _return:
                for item in self.items:
                    try:
                    # self.datas[item].append(l[self.items.index(item)])
                        self.datas[item].append(l[0])
                        l.remove(l[0])
                    except:
                        break



GET_TYPE_DATE = 21
GET_TYPE_DATETIME = 22
GET_TYPE_TIME = 23
GET_TYPE_DIGITLE = 24
GET_TYPE_LONGDIGITLE = 25

class settingConfig:
    def __init__(self, _file):
        self.config = None
        self.src = _file
        self.initConfig()

    def initConfig(self):
        self.config = configparser.ConfigParser()
        try:
            self.config.read_file(codecs.open(self.src,"r","gbk"))
        except Exception as e:
            self.config = None
            logging.error(e)


    def saveConfig(self, datas):
        for data in datas:
            s = self.config.sections()
            if data[0] not in s:
                self.config.add_section(data[0])
            self.config.set(data[0], data[1], value=data[2])
        self.config.write(codecs.open(self.src,"w","gbk"))
        # with open(self.src, 'a') as configfile:
        #     self.config.write(configfile)



_vt_conf = settingConfig('vt.conf')
_sys_conf = settingConfig('setting\\default.ini')

READY_MODE_LOG = 31
READY_MODE_DB = 32
READY_MODE_PATH = 33


class logic:
    def __init__(self):
        self.logRootPath = None   # 日志根目录
        self.dataRootPath = None   # 数据根目录
        self.endDate = datetime.datetime.max
        self.startDate = datetime.datetime.min
        self.zjLogFiles = list()
        self.xtLogFiles = list()
        self.cxLogFiles = list()
        self.resultTxts = list()
        self.calibrationFileRootPath = None
        self.apiRootPath = None
        self.realtimeDataRootPath = None

    def _start(self, startDate, endDate, qResult):
        self.startDate = startDate
        self.endDate = endDate
        self.ready()
        m = multiprocessing.Manager()
        _index0 = m.Queue()
        _index1 = m.Queue()
        _index2 = m.Queue()
        _index3 = m.Queue()
        _index4 = m.Queue()
        _index5 = m.Queue()
        _index6 = m.Queue()

        result_checkMeasureCompleteness = m.list()
        result_checkOverLimit3DPerformance = m.list()
        result_checkTransmitProcess = m.list()
        result_checkOverLimitCarValidation = m.list()
        result_checkEquipmentStatusProcess = m.list()
        result_checkEquipmentStatusProcess2 = m.list()
        result_checkEquipmentStatusProcess3 = m.list()
        result_checkStandardTrainKindError = m.dict()
        
        
        poolcount = multiprocessing.cpu_count()
        allresult = []
        with multiprocessing.Pool(poolcount) as p:
            try:
                logging.info('>> r_checkEquipmentStatusProcess')
                [_index0.put(f) for f in self.zjLogFiles]
                r_checkEquipmentStatusProcess = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkEquipmentStatusProcess,
                            _index0,
                            5,
                            result_checkEquipmentStatusProcess
                        )
                    ] * poolcount
                )

                logging.info('>> r_checkEquipmentStatusProcess2')
                [_index5.put(f) for f in self.xtLogFiles]
                r_checkEquipmentStatusProcess2 = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkEquipmentStatusProcess2,
                            _index5,
                            5,
                            result_checkEquipmentStatusProcess2
                        )
                    ] * poolcount
                )

                logging.info('>> r_checkEquipmentStatusProcess3')
                [_index6.put(f) for f in self.zjDataFiles]
                r_checkEquipmentStatusProcess3 = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkEquipmentStatusProcess3,
                            _index6,
                            5,
                            result_checkEquipmentStatusProcess3
                        )
                    ] * poolcount
                )

                logging.info('>> r_checkTransmitProcess')
                r_checkTransmitProcess = p.apply_async(
                    self._checkTransmitProcess,
                    (
                        result_checkTransmitProcess,
                    )
                )

                logging.info('>> r_checkTrainNumberIdentification')
                r_checkTrainNumberIdentification = p.apply_async(
                    self._checkTrainNumberIdentification,
                    (
                        self.selectionDirs,
                    )
                )

                logging.info('>> r_checkOverLimitCarValidation')
                [_index1.put(f) for f in self.selectionDirs]
                r_checkOverLimitCarValidation = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkOverLimitCarValidation,
                            _index1,
                            5,
                            result_checkOverLimitCarValidation
                        )
                    ] * poolcount
                )

                logging.info('>> r_checkCalibrationCompleteness')
                r_checkCalibrationCompleteness = p.apply_async(
                    self._checkCalibrationCompleteness
                )


                logging.info('>> r_checkOverLimit3DPerformance')
                [_index3.put(f) for f in self.cxLogFiles]
                r_checkOverLimit3DPerformance = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkOverLimit3DPerformance,
                            _index3,
                            5,
                            result_checkOverLimit3DPerformance
                        )
                    ]
                )

                logging.info('>> r_checkCalibrationError')
                r_checkCalibrationError = p.apply_async(
                    self._checkCalibrationError
                )


                logging.info('>> r_checkMeasureCompleteness')
                [_index4.put(f) for f in self.selectionDirs]
                r_checkMeasureCompleteness = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkMeasureCompleteness,
                            _index4,
                            5,
                            result_checkMeasureCompleteness
                        )
                    ]
                )

                logging.info('>> r_checkStandardTrainKindError')
                [_index2.put(f) for f in self.selectionDirs]
                r_checkStandardTrainKindError = p.starmap_async(
                    self.workProcess,
                    [
                        (
                            self._checkStandardTrainKindError,
                            _index2,
                            5,
                            result_checkStandardTrainKindError
                        )
                    ]
                )
            except Exception as e:
                logging.error('_start > error > ' + repr(e))

            try:
                allresult.append(r_checkEquipmentStatusProcess.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkTransmitProcess.get())
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkTrainNumberIdentification.get(timeout=5))
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkOverLimitCarValidation.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkCalibrationCompleteness.get(timeout=5))
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkOverLimit3DPerformance.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkCalibrationError.get(timeout=5))
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkMeasureCompleteness.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkStandardTrainKindError.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkEquipmentStatusProcess2.get()[0])
            except:
                allresult.append(-1)
            try:
                allresult.append(r_checkEquipmentStatusProcess3.get()[0])
            except:
                allresult.append(-1)

        self.handleCheckEquipmentStatusResult((allresult[0], allresult[10]), qResult)
        self.handlecheckTransmitProcess(allresult[1], qResult)
        self.handleTrainNoRate(allresult[2], qResult)
        self.handleCheckOverLimitCarValidation(allresult[3], qResult)
        self.handleCheckCalibrationCompleteness(allresult[4], qResult)
        self.handleCheckOverLimit3DPerformance(allresult[5], qResult)
        self.handleCheckCalibrationError(allresult[6], qResult)
        self.handleCheckMeasureCompleteness(allresult[7], qResult)
        self.handleCheckStandardError(allresult[8], qResult)
        self.handleCheckEquipmentStatusResult2(allresult[9], qResult)
        self._outputTxt()


    def _outputTxt(self):
        if len(self.resultTxts) > 0:
            _tmp = dict()
            for l in self.resultTxts:
                if l[0] in _tmp.keys():
                    _tmp[l[0]].append((l[1], l[2]))
                else:
                    _tmp[l[0]] = [(l[1], l[2])]
            reportname = self.time2str(datetime.datetime.now(), mode=GET_TYPE_LONGDIGITLE) + '.txt'
            with open(reportname, 'w') as f:
                for key in _tmp.keys():
                    for l in _tmp[key]:
                        if l[1] is None or l[0] is None:
                            continue
                        f.write('【' + l[0] + '】\n')
                        f.write(l[1])
                        f.write('\n')



    def handleCheckStandardError(self, _result, qResult):
        #  3242x3143
        import multiprocessing.pool
        resultText = ''
        if _result == -1:
            qResult.put((2, 2, '超时'))
        else:
            # if not isinstance(_result, multiprocessing.pool.MapResult):
            for key in _result.keys():
                for k in _result[key]:
                    if _result.keys().index(key) == 0:
                        resultText += '【车型】 %s' % (key)
                    else:
                        resultText += '\n【车型】 %s' % (key)
                    resultText += '\n高度(最大\最小\平均)：%.1f,%.1f,%.1f' % (k[0], k[1], k[2])
                    resultText += '\n左宽(最大\最小\平均)：%.1f,%.1f,%.1f' % (k[3], k[4], k[5])
                    resultText += '\n右宽(最大\最小\平均)：%.1f,%.1f,%.1f' % (k[6], k[7], k[8])
            self.resultTxts.append(('测量性能验证', '标准车型测量误差验证', resultText))
            qResult.put((2, 2,resultText))
            # else:
            #     qResult.put((2, 2, '超时'))

    def handleCheckMeasureCompleteness(self, _result, qResult):
        logging.debug('> handleCheckMeasureCompleteness')
        import multiprocessing.managers
        if _result == -1 or not isinstance(_result, multiprocessing.managers.ListProxy):
            qResult.put((1,1,'超时'))
        else:
            invalid = []
            for l in _result:
                try:
                    l.index(-1)
                    invalid.append(-1)
                    continue
                except:
                    pass
                if l[1] != l[3] or l[1] != l[5] or l[2] != l[6]:
                    invalid.append(-1)
                    continue
                if l[7] != l[1] + l[2]:
                    invalid.append(-1)
                    continue
                if l[4].count(True) != 6:
                    invalid.append(-1)
                    continue
                if l[7] is False:
                    invalid.append(-1)
                    continue
            amount = len(_result)
            invalidAmount = len(invalid)
            resultText = '共计 %d 列过车，其中测量数据缺失 %d 列。' % (amount, invalidAmount)
            self.resultTxts.append(('数据质量检查', '测量数据完整性检查', resultText))
            qResult.put((1,1,resultText))


            
    def handleCheckCalibrationError(self, _result, qResult):
        logging.debug('> handleCheckCalibrationError')
        if _result == -1:
            qResult.put((2, 0, '超时'))
        else:
            for line in _result.keys():
                resultText1 = '左雷达 高度误差：%s  宽度误差：%s' % (_result[line][0], _result[line][1])
                resultText1 += '\n右雷达 高度误差：%s  宽度误差：%s' % (_result[line][2], _result[line][3])
                resultText2 = '左雷达 高度(最大\最小\平均)：%s, %s, %s' % (_result[line][4][2], _result[line][4][1], _result[line][4][0])
                resultText2 += '\n左雷达 宽度(最大\最小\平均)：%s, %s, %s' % (_result[line][5][2], _result[line][5][1], _result[line][5][0])
                resultText2 += '\n右雷达 高度(最大\最小\平均)：%s, %s, %s' % (_result[line][6][2], _result[line][6][1], _result[line][6][0])
                resultText2 += '\n右雷达 宽度(最大\最小\平均)：%s, %s, %s' % (_result[line][7][2], _result[line][7][1], _result[line][7][0])
                self.resultTxts.append(('测量性能验证', '一次标定误差验证', resultText1))
                self.resultTxts.append(('测量性能验证', '二次标定误差验证', resultText2))
                qResult.put((2,0,resultText1))
                qResult.put((2,1,resultText2))

    def handleCheckOverLimit3DPerformance(self, _result, qResult):
        logging.debug('> handleCheckOverLimit3DPerformance')
        if _result == -1:
            qResult.put((2, 4, '超时'))
        else:
            _limit = int(_vt_conf.config.get('超限报警车3D图', '时限'))
            def _filter(x):
                return x>=_limit
            lst = list(filter(_filter, _result))
            resultText = '图像生成时间小于 %d 秒共 %d 辆' % (_limit, len(_result) - len(lst))
            resultText += '，超时共 %d 辆' % (len(lst))
            self.resultTxts.append(('测量性能验证', '超限报警车3D图性能验证', resultText))
            qResult.put((2,4,resultText))
        
    def handleCheckCalibrationCompleteness(self, _result, qResult):
        logging.debug('> handleCheckCalibrationCompleteness')
        if _result == -1:
            qResult.put((1,0, '超时'))
        else:
            self.resultTxts.append(('数据质量检查', '标定完整性检查', _result))
            qResult.put((1,0,_result))

    def handleCheckOverLimitCarValidation(self, _result, qResult):
        logging.debug('> handleCheckOverLimitCarValidation')
        if _result == -1:
            qResult.put((2,2,'超时'))
        else:
            N_count = 0
            P_count = 0
            C_count = 0
            for i in _result:
                if i[1] == 'C':
                    C_count += 1
                elif i[1] == 'P':
                    P_count += 1
                elif i[1] == 'N':
                    N_count += 1
            c_limit = int(_vt_conf.config.get('超限报警车阈值', '敞车').strip())
            p_limit = int(_vt_conf.config.get('超限报警车阈值', '棚车'))
            resultText = ''
            resultText += '敞车报警： ' + str(C_count) + '辆。\n'
            resultText += '棚车报警： ' + str(P_count) + '辆。\n'
            resultText += '平车报警： ' + str(N_count) + '辆。'
            if C_count > c_limit:
                resultText += '\n警告：敞车报警数量超过报警值！'
            if P_count > p_limit:
                resultText += '\n警告：棚车报警数量超过报警值！'
            if N_count < (C_count + P_count):
                resultText += '\n警告：其他车型报警数超过平车报警数！'
            self.resultTxts.append(('测量性能验证', '超限报警车型验证', resultText))

            qResult.put((2,3, resultText))
            
    
    def handleTrainNoRate(self, _result, qResult):
        logging.debug('> handleTrainNoRate')
        if _result == -1:
            qResult.put((1,3,'超时'))
        else:
            
            son = int(_result[0])
            mom = int(_result[1])
            try:
                _result = son / mom * 100
            except ZeroDivisionError:
                _result = 0
            resultText = '%3.2f%% (有效：%d / 总量：%d)' % (_result, son, mom)
            self.resultTxts.append(('数据质量检查', '车号识别率', resultText))
            qResult.put((1,3,resultText))
    
    def handlecheckTransmitProcess(self, _result, qResult):
        import multiprocessing.managers
        logging.debug('> handlecheckTransmitProcess')
        errorText = ''
        if _result == -1 or not isinstance(_result, multiprocessing.managers.ListProxy):
            errorText = '超时'
        else:
            if len(_result) == 0:
                errorText = '共计 0 列过车'
            else:
                _datas = _result[0]
                _trains = []
                for train in list(_datas.keys()):
                    if self._filter_data(train):
                        _trains.append(train)
                _sum_car = len(_trains)
                errorText = '共计 %d 列过车，其中' % (_sum_car,)
                r = dict()
                for key in _trains:
                    for _key in _datas[key].keys():
                        if _key not in r.keys():
                            r[_key] = [[], []]
                        r[_key][0].append(_result[0][key][_key][0])
                        r[_key][1].append(_result[0][key][_key][1])
                # print(r)
                for r_key in r.keys():
                    if '实时' in r_key:
                        errorText += '\n%s 成功 %d 列 （ %d 辆），失败 %d 辆。' % (r_key, len(r[r_key][0]), sum(r[r_key][0]) + sum(r[r_key][1]), sum(r[r_key][1]))
                    if '标准' in r_key:
                        errorText += '\n%s 成功 %d 列，失败 %d 列。' % (r_key, sum(r[r_key][0]) + sum(r[r_key][1]), sum(r[r_key][1]))
        self.resultTxts.append(('数据质量检查', '传输数据完整性检查', errorText))
        qResult.put((1,2,errorText))
      
    def handleCheckEquipmentStatusResult2(self, _result, qResult):
        logging.debug('> handleCheckEquipmentStatusResult2')
        if _result == -1:
            qResult.put((0,1,'超时'))
        else:
            _tmp = []
            [_tmp.extend(x) for x in _result]
            _start = sum([i[0] for i in _result])
            _end = sum([i[1] for i in _result])
            if _start - _end - 1 > -1:
                resultText = '累计正常启动 %d 次，正常退出 %d 次，出现异常 %d 次' % (_start, _end, _start - _end - 1)
            else:
                resultText = '累计正常启动 %d 次，正常退出 %d 次，出现异常 0 次' % (_start, _end)
            self.resultTxts.append(('设备状态检查', '测量系统运行状态检查', resultText))
            qResult.put((0,2,resultText))

    def handleCheckEquipmentStatusResult(self, _result, qResult):
        logging.debug('> handleCheckEquipmentStatusResult')
        _tmp = _result
        if _tmp == -1:
            qResult.put((0, 0, '超时'))
            # qResult.put((0, 1, '超时'))
            qResult.put((0, 2, '超时'))
        elif isinstance(_tmp, tuple):
            _serialError_1 = sum([i[1] for i in _tmp[0]])
            _serialError_2 = sum([i[2] for i in _tmp[0]])
            _serialData_1 = [i[1] for i in _tmp[1]].count(1)
            _leftLadarError_1 = sum([i[3] for i in _tmp[0]])
            _leftLadarError_2 = sum([i[4] for i in _tmp[0]])
            _rightLadarError_1 = sum([i[5] for i in _tmp[0]])
            _rightLadarError_2 = sum([i[6] for i in _tmp[0]])
            _serialErrorDays = dict()
            _ladarErrorDays = dict()
            for _item in _tmp[0]:
                if _item[1] > 0 or _item[2] > 0:
                    if _item[0][:8] not in _serialErrorDays.keys():
                        _serialErrorDays[_item[0][:8]] = 1
                    else:
                        _serialErrorDays[_item[0][:8]] += 1
                if _item[3] > 0 or _item[4] > 0 or _item[5] > 0 or _item[6] > 0:
                    if _item[0][:8] not in _ladarErrorDays.keys():
                        _ladarErrorDays[_item[0][:8]] = 1
                    else:
                        _ladarErrorDays[_item[0][:8]] += 1
            for _item2 in _tmp[1]:
                if _item2[0][:8] not in _serialErrorDays.keys():
                    _serialErrorDays[_item2[0][:8]] = 1
                else:
                    _serialErrorDays[_item2[0][:8]] += 1
            resultText1 = '发现严重异常 %d 次，一般异常 %d 次，累计故障天数为 %d 天。' % (_serialError_1 + _serialData_1, _serialError_2, len(_serialErrorDays.keys()))
            resultText2 = '发现严重异常 %d 次，一般异常 %d 次，累计故障天数为 %d 天。' % (_leftLadarError_1 + _rightLadarError_1, _leftLadarError_2 + _rightLadarError_2, len(_ladarErrorDays.keys()))
            self.resultTxts.append(('设备状态检查', '雷达网络运行状态检查', resultText2))
            self.resultTxts.append(('设备状态检查', '串口运行状态检查', resultText1))
            qResult.put((0, 1, resultText2))
            qResult.put((0, 0, resultText1))
        else:
            qResult.put((0, 1, repr(_result)))
            qResult.put((0, 0, repr(_result)))

    def _filter_log(self, x):
        _s_log = self.time2str(self.startDate)
        _e_log = self.time2str(self.endDate)
        return x >= _s_log and x <= _e_log

    def _filter_data(self, x):
        _s_data = self.time2str(self.startDate, mode=GET_TYPE_DIGITLE)
        _e_data = self.time2str(self.endDate, mode=GET_TYPE_DIGITLE)
        return x >= _s_data and x <= _e_data

    def _getFiles(self, rootPath, keyword):
        logging.debug('> _getFiles')
        rr = []
        for _root, _dirs, _files in os.walk(rootPath):
            for f in  _files:
                if keyword == 'log':
                    if f[:2] in ('2D', '3D'):
                        # print('23D >', f)
                        if self._filter_log(f[2:]):
                                rr.append(os.path.join(_root, f))
                    else:
                        if self._filter_log(f):
                            rr.append(os.path.join(_root, f))
                else:
                    if keyword in f:
                        rr.append(os.path.join(_root, f))
            if keyword == 'data':
                for _dir in _dirs:
                    if self._filter_data(_dir):
                        rr.append(_dir)
            if keyword == 'selfCheckData':
                for f in _files:
                    if 'con'.upper() in f.upper() and self._filter_data(f.split('-')[2]):
                        rr.append(os.path.join(_root, f))
            break
        logging.debug('_getFiles >')
        return rr
                

    def ready(self):
        logging.debug('> ready')        
        self.logRootPath = os.path.normpath(_vt_conf.config.get('目录', '日志根目录'))
        self.zjLogFiles = self._getFiles(os.path.join(self.logRootPath, 'ZJLog'), 'log')
        self.xtLogFiles = self._getFiles(os.path.join(self.logRootPath, 'XTLog'), 'log')
        self.cxLogFiles = self._getFiles(os.path.join(self.logRootPath, 'CXLog'), 'log')
        zjDataRoot = _sys_conf.config.get('Rout Set', 'DataDeStar')
        self.zjDataFiles = self._getFiles(os.path.normpath(zjDataRoot.replace('"','')), 'selfCheckData')
        self.dataRootPath = os.path.normpath(_vt_conf.config.get('目录', '数据根目录'))
        self.selectionDirs = self._getFiles(self.dataRootPath, 'data')
        logging.debug('zj -> ' + repr(self.zjLogFiles))
        logging.debug('zjdata -> ' + repr(self.zjDataFiles))
        logging.debug('xt -> ' + repr(self.xtLogFiles))
        logging.debug('cx -> ' + repr(self.cxLogFiles))
        logging.debug('dataRoot -> ' + repr(self.dataRootPath))
        logging.debug('selectionDirs -> ' + repr(self.selectionDirs))

        logging.debug('ready >')
        
    
    def str2time(self, _str):
        _year = int(_str[:4])
        _month = int(_str[5:7])
        _day = int(_str[8:10])
        _hour = int(_str[11:13])
        _min = int(_str[14:16])
        _second = int(_str[17:19])
        _return = datetime.datetime(_year, _month, _day, _hour, _min, _second)
        return _return
    
    def str2time2(self, _str):
        # 20170726163700
        _year = int(_str[:4])
        _month = int(_str[4:6])
        _day = int(_str[6:8])
        _hour = int(_str[8:10])
        _min = int(_str[10:12])
        _second = int(_str[12:14])
        _return = datetime.datetime(_year, _month, _day, _hour, _min, _second)
        return _return
    
    def time2str(self, _time, mode=GET_TYPE_DATE):
        _return = None
        if isinstance(_time, datetime.datetime):
            _year = _time.strftime('%Y')
            _month = _time.strftime('%m')
            _day = _time.strftime('%d')
            _hour = _time.strftime('%H')
            _minute = _time.strftime('%M')
            _second = _time.strftime('%S')
            _msecond = _time.strftime('%f')
            if mode == GET_TYPE_DATETIME:
                _return = '%s年%s月%s日%s时%s分%s秒' % (_year, _month, _day, _hour, _minute, _second)
            elif mode == GET_TYPE_DATE:
                _return = '%s年%s月%s日' % (_year, _month, _day)
            elif mode == GET_TYPE_TIME:
                _return = '%s时%s分%s秒' % (_hour, _minute, _second)
            elif mode == GET_TYPE_DIGITLE:
                _return = '%s%s%s%s%s%s' % (_year, _month, _day, _hour, _minute, _second)
            elif mode == GET_TYPE_LONGDIGITLE:
                _return = '%s%s%s%s%s%s%s' % (_year, _month, _day, _hour, _minute, _second, _msecond)
        return _return
    
    def workProcess(self, func, multiQueue, count, resultlist):
        i = 0
        tasks = []
        while i<=count:
            tasks.append(func(multiQueue, resultlist))
            i += 1
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()
        return resultlist
    
    """
    标定完整性检查
    """
    def _checkCalibrationCompleteness(self):
        logging.debug('> _checkCalibrationCompleteness')
        _return = None
        _file = 'LidarCal.xml'
        try:
            logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
            if os.path.exists(_file):
                _data = XmlReader(_file).data
                h_data = self._handleXML_calibrationConfig(_data, returnItem='status')
                tmp = []
                for x in h_data.keys():
                    x_i = list(h_data.keys()).index(x)
                    tmp.awppend('%s  一次标定：%s  二次标定：%s ' % (x, '完成' if h_data[x][0]=='1' else '未完成', '完成' if h_data[x][1] =='1' else '未完成') + ('' if x_i == len(list(h_data.keys()))-1 else '\n'))
                resultText = ''.join(tmp)
                _return = resultText
            else:
                logging.error('未发现标定文件!')
                    
        except Exception as e:
            logging.error(e)
        finally:
            return _return

    """
    测量数据完整性检查
    """
    def _checkMeasureCompleteness(self, q, l):
        logging.debug('> _checkMeasureCompleteness')
        while 1:
            try:
                if q.empty():
                    break
                _root = os.path.normpath(os.path.join(self.dataRootPath, q.get_nowait()))
                _date = _root.split('\\')[-1]
                rl = [_date, -1, -1, -1, [], -1, -1, -1, -1]
                imgs = []
                file_exists = []
                for _root, _dirs, _files in os.walk(_root):
                    for _file in _files:
                        if '.jpg' in _file:
                            imgs.append(_file)
                    break
                rl[3] = len(imgs)
                _prefix = self.time2str(self.str2time2(_date), mode=GET_TYPE_DATETIME)
                f_index = os.path.join(_root, 'index.txt')
                file_exists.append(os.path.exists(f_index))
                f_slant = os.path.join(_root, _prefix + 'slant_lms.txt')
                file_exists.append(os.path.exists(f_slant))
                f_TmeasuredData = os.path.join(_root, _prefix + 'TmeasuredData_lms.txt')
                file_exists.append(os.path.exists(f_TmeasuredData))
                f_AllScanData = os.path.join(_root, _prefix + 'AllScanData_lms.lms')
                file_exists.append(os.path.exists(f_AllScanData))
                f_log = os.path.join(_root, 'log.txt')
                file_exists.append(os.path.exists(f_log))
                f_ok = os.path.join(_root, 'ok.txt')
                file_exists.append(os.path.exists(f_ok))
                rl[4] = file_exists
                if rl[4][0] is False:
                    l.append(rl)
                    continue
                indexData = TxtReader(f_index).data
                h_indexData = self._handleTxt_indexInfo(indexData)
                amountIndex = len(h_indexData['index'])
                rl[1] = amountIndex
                if rl[4][1] is False:
                    l.append(rl)
                    continue
                slantData = TxtReader(f_slant).data
                h_slantData = self._handleTxt_slant(slantData)
                warningSlant = len(h_slantData)
                rl[2] = warningSlant
                yield
                _2dimgs = []
                _3dimgs = []
                _xmls = []
                realRoot = os.path.join(_root, 'cxsb')
                for _root, _dirs, _files in os.walk(realRoot):
                    for _file in _files:
                        if '.xml' in _file:
                            _xmls.append(os.path.join(realRoot, _file))
                        if '.jpg' in _file and '3D' in _file:
                            _3dimgs.append(os.path.join(realRoot, _file))
                        if '.jpg' in _file and '3D' not in _file:
                            _2dimgs.append(os.path.join(realRoot, _file))
                    break
                f_realok = os.path.exists(os.path.join(realRoot, 'zbok.txt'))

                rl[5] = len(_2dimgs)
                rl[6] = len(_3dimgs)
                rl[7] = len(_xmls)
                rl[8] = f_realok
                l.append(rl)
            except Exception as e:
                logging.error(e)
                break
        
        
    
    
    """
    车号识别率
    """
    def _checkTrainNumberIdentification(self, lstIndex):
        logging.debug('> _checkTrainNumberIdentification')
        try:
                
            _lst_index = []
            for f in lstIndex:
                try:
                    iData = TxtReader(os.path.join(self.dataRootPath, f, 'index.txt'))
                    _lst_index.extend(self._handleTxt_indexInfo(iData.data)['trainno'])
                except Exception as e:
                    logging.error(repr(e))
                    continue
            mom = len(_lst_index)
            son = mom - _lst_index.count('X'*20)
            return son, mom
                
        except Exception as e:
            logging.error('<<< ERROR >>>')
            logging.error('iData >' + repr(iData))
            logging.error('_lst_index >' + repr(_lst_index))
            logging.error("_lst_index.count('X'*20) >" + repr(_lst_index.count('X'*20)))
            logging.error(repr(e))
    
    
    """
    标定误差验证
    """
    def _checkCalibrationError(self):
        logging.debug('> _checkCalibrationError')
        _file = 'LidarCal.xml'
        try:
            logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
            logging.debug('LidarCal.xml > ' + repr(os.path.exists(_file)))
            if os.path.exists(_file):
                _data = XmlReader(_file).data
                h_data = self._handleXML_calibrationConfig(_data, returnItem='data')
                return h_data
        except Exception as e:
            logging.debug('_data >' + repr(_data))
            logging.debug('h_data >' + repr(h_data))
            logging.error(e)

            return -1

    """
    标准车型测量误差验证
    """
    @asyncio.coroutine
    def _checkStandardTrainKindError(self, q, d):
        logging.debug('> _checkStandardTrainKindError')
        while 1:
            try:
                if q.empty():
                    break
                rootDir = os.path.join(self.dataRootPath, q.get_nowait())
                _date = os.path.normpath(rootDir).split('\\')[-1]
                stdTrains = [option for option in _vt_conf.config['标准车型']]
                logging.debug(''.join([str(os.getpid()), ' > ', rootDir, ' > ', str(time.time())]))
                f_index = os.path.join(rootDir, 'index.txt')
                iData = TxtReader(f_index).data
                h_iData = self._handleTxt_indexInfo(iData)
                tmp = dict()
                kk = [x[:7] for x in h_iData['trainno']]
                for x in kk:
                    for y in stdTrains:
                        try:
                            if x.index(y.upper() + ' ') >= 0:
                                k_index = kk.index(x)
                                if y in tmp.keys():
                                    tmp[y].append((_date, h_iData['index'][k_index]))
                                else:
                                    tmp[y] = [(_date, h_iData['index'][k_index])]
                        except Exception as e:
                            pass
                tmp2 = dict()
                for car in tmp.keys():
                    tmp2[car] = list()
                    for c in tmp[car]:
                        _src = (
                            int(c[1]),
                            _date.encode(encoding='utf-8'),
                            car.encode(encoding='utf-8')
                        )
                        _api = ApiReader(_src).data
                        _r = self._handleAPI_measure(_api)
                        # print(dir(_api.contents))
                        tmp2[car].append(_r)
                for car in tmp2.keys():
                    _H = float(_vt_conf.config.get('标准车型', car).split('x')[0])
                    _leftW = float(_vt_conf.config.get('标准车型', car).split('x')[1]) / 2
                    _rightW = float(_vt_conf.config.get('标准车型', car).split('x')[1]) / 2
                    max_h = [x[0] for x in tmp2[car]]
                    min_h = [x[1] for x in tmp2[car]]
                    avg_h = [x[2] for x in tmp2[car]]
                    max_lw = [x[0] for x in tmp2[car]]
                    min_lw = [x[1] for x in tmp2[car]]
                    avg_lw = [x[2] for x in tmp2[car]]
                    max_rw = [x[0] for x in tmp2[car]]
                    min_rw = [x[1] for x in tmp2[car]]
                    avg_rw = [x[2] for x in tmp2[car]]
                    if car in d.keys():
                        d[car].append(
                            (
                                [abs(x) for x in [
                                sum(max_h) / len(max_h) - _H,
                                sum(min_h) / len(min_h) - _H,
                                sum(avg_h) / len(avg_h) - _H,
                                sum(max_lw) / len(max_lw) - _leftW,
                                sum(min_lw) / len(min_lw) - _leftW,
                                sum(avg_lw) / len(avg_lw) - _leftW,
                                sum(max_rw) / len(max_rw) - _rightW,
                                sum(min_rw) / len(min_rw) - _rightW,
                                sum(avg_rw) / len(avg_rw) - _rightW]]
                            )
                        )
                    else:
                        d[car] = [
                            (
                                [abs(x) for x in [
                                sum(max_h) / len(max_h) - _H,
                                sum(min_h) / len(min_h) - _H,
                                sum(avg_h) / len(avg_h) - _H,
                                sum(max_lw) / len(max_lw) - _leftW,
                                sum(min_lw) / len(min_lw) - _leftW,
                                sum(avg_lw) / len(avg_lw) - _leftW,
                                sum(max_rw) / len(max_rw) - _rightW,
                                sum(min_rw) / len(min_rw) - _rightW,
                                sum(avg_rw) / len(avg_rw) - _rightW]]
                            )
                        ]
            except Exception as e:
                logging.error(e)
                break


    
    """
    超限报警车3D图性能验证
    """
    def _checkOverLimit3DPerformance(self, q, l):
        logging.debug('> _checkOverLimit3DPerformance')
        while 1:
            try:
                if q.empty():
                    break
                
                _file = q.get_nowait()
                logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
                if '3D' in _file:
                    _3ddata = TxtReader(_file).data
                    yield
                    self._handleTxt_3dlog(_3ddata, l)
            except Exception as e:
                logging.error(e)
                break
    
    

    """
    传输数据完整性检查
    """
    def _checkTransmitProcess(self, l):
        logging.debug('> _checkTransmitProcess')
        try:
            ip = _vt_conf.config.get('数据库', '服务器')
            user = _vt_conf.config.get('数据库', '登录名')
            pwd = _vt_conf.config.get('数据库', '密码')
            db = _vt_conf.config.get('数据库', '数据库')
            _sql = 'select COUNT(*) as times,[ComeTrain] as date,[Status] as sts, [TranType] as cata FROM [Tran].[dbo].[cs_TransmitMain] group by [ComeTrain],TranType,[Status]'
            datas = DbReader((ip, user,pwd,db,_sql)).data
            self._handleDb_transport(datas, l)
        except Exception as e:
            logging.error(e)
        finally:
            return l
            
    """
    超限报警车型验证
    """
    @asyncio.coroutine
    def _checkOverLimitCarValidation(self, q, l):
        logging.debug('> _checkOverLimitCarValidation')
        while 1:
            try:
                if q.empty(): 
                    break
                _rootPath = os.path.join(self.dataRootPath, q.get_nowait())
                iFile = os.path.join(_rootPath, 'index.txt')
                sFile = None
                for _root, _dirs, _files in os.walk(_rootPath):
                    for _file in _files:
                        if 'slant' in _file:
                            sFile = os.path.join(_root, _file)
                            break
                    break
                if sFile is None:
                    break
                sData = TxtReader(sFile).data
                rS = self._handleTxt_slant(sData)
                yield
                fData = TxtReader(iFile).data
                for i in rS:
                    self._handleTxt_indexInfo(fData, returnItem=i, listproxy=l)
                
            except Exception as e:
                pass


    """
    测量系统运行状态检查
    """
    @asyncio.coroutine
    def _checkEquipmentStatusProcess2(self, q, l):
        logging.debug('> _checkEquipmentStatusProcess2')
        while 1:
            try:
                if q.empty():
                    break
                _file = q.get_nowait()
                logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
                if os.path.exists(_file):
                    _data = TxtReader(_file).data
                    yield
                    self._handleTxt_systemLog(_data, l)

            except Exception as e:
                logging.error('<<< ERROR >>>')
                logging.debug(repr(e))
                break


    @asyncio.coroutine
    def _checkEquipmentStatusProcess3(self, q, l):
        logging.debug('> _checkEquipmentStatusProcess3')
        while 1:
            try:
                if q.empty():
                    break
                _file = q.get_nowait()
                logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
                if os.path.exists(_file):
                    _data = TxtReader(_file).data
                    yield
                    _date = _file.split('-')[2][:-4]
                    self._handleTxt_selfCheckData(_data, l, _date)
                else:
                    l.append(0)
            except Exception as e:
                logging.debug('<<< ERROR >>>')
                logging.debug('_file > ' + repr(_file))
                logging.debug('q > ' + repr(q))
                logging.debug('l > ' + repr(l))
                logging.error(e)
                break

    """
    雷达网络运行状态检查
    测量系统运行状态检查
    串口运行状态检查
    """
    @asyncio.coroutine
    def _checkEquipmentStatusProcess(self, q, l):
        logging.debug('> _checkEquipmentStatusProcess')
        while 1:
            try:
                if q.empty():
                    break
                _file = q.get_nowait()
                logging.debug(''.join([str(os.getpid()), ' > ', _file, ' > ', str(time.time())]))
                if os.path.exists(_file):
                    _data = TxtReader(_file).data
                    yield
                    self._handleTxt_selfCheckLog(_data, l)
                else:
                    l.append([0,0,0,0,0,0])
            except Exception as e:
                logging.debug('<<< ERROR >>>')
                logging.debug('_file > ' + repr(_file))
                logging.debug('q > ' + repr(q))
                logging.debug('l > ' + repr(l))
                logging.error(e)
                break
    
    
    """
    处理数据
    """

    def _handleAPI_measure(self, datas):
        logging.debug('> _handleAPI_measure')
        _return = None
        try:
            logging.debug('> datas > ' + repr(datas))
            _h = datas.contents.m_TrHeightData.decode().split(',')
            _lw = datas.contents.m_TrLeftWidthData.decode().split(',')
            _rw = datas.contents.m_TrRightWidthData.decode().split(',')
            avg_h = sum([float(x) for x in _h])/len(_h)
            avg_lw = sum([float(x) for x in _lw])/len(_lw)
            avg_rw = sum([float(x) for x in _rw])/len(_rw)
            max_h = max([float(x) for x in _h])
            max_lw = max([float(x) for x in _lw])
            max_rw = max([float(x) for x in _rw])
            min_h = min([float(x) for x in _h])
            min_lw = min([float(x) for x in _lw])
            min_rw = min([float(x) for x in _rw])
            _return = (max_h, min_h, avg_h, max_lw, min_lw, avg_lw, max_rw, min_rw, avg_rw)
        except Exception as e:
            logging.debug('<<< ERROR >>>')
        finally:
            return _return


    
    """
    处理数据库中传输记录
    """
    def _handleDb_transport(self, datas, rl):
        logging.debug('> _handleDb_transport')
        try:
            if datas is None:
                raise Exception('data is none')
            _tmp = dict()
            for l in datas:
                if l[1] not in _tmp.keys():
                    _tmp[l[1]] = dict()
                if l[3] not in _tmp[l[1]].keys():
                    _tmp[l[1]][l[3]] = [0, 0]
                if '完成' in l[2]:
                    _tmp[l[1]][l[3]][0] = l[0]
                else:
                    _tmp[l[1]][l[3]][1] = l[0]

            rl.append(_tmp)
        except Exception as e:
            logging.error(e)

    """
    处理标定配置文件
    """
    def _handleXML_calibrationConfig(self, datas, returnItem='data'):
        logging.debug('> _handleDb_transport')
        try:
            if datas is None:
                raise Exception('data is none')
            _data = dict()
            _status = dict()
            for x in datas:
                if x[2][1] == '0':
                    continue
                x_index = datas.index(x)  # 线路
                _data[datas[x_index][2][0]] = []
                _status[datas[x_index][2][0]] = datas[x_index][0]           
                for xx in x[1]:
                    xx_index = x[1].index(xx)  # l1,r1,l2,r2
                    if xx_index < 2:
                        for xxx in xx:
                            xxx_index = xx.index(xxx) # road_radar_dis:0, radarheight:1
                            diff = abs(float(xxx[1]) - float(xxx[0]))
                            _data[datas[x_index][2][0]].append(diff)
                    else:
                        for xxx in xx:
                            xxx_index = xx.index(xxx)
                            _avg = float(xxx[1]) - float(xxx[0])
                            _min = float(xxx[2]) - float(xxx[0])
                            _max = float(xxx[3]) - float(xxx[0])
                            _data[datas[x_index][2][0]].append(list(abs(x) for x in [_avg,_min,_max]))
            if returnItem == 'data':
                return _data
            elif returnItem == 'status':
                return _status
        except Exception as e:
            logging.error(e)

    def _handleTxt_selfCheckData(self, datas, rl, _date):
        logging.debug('> _handleTxt_selfCheckData')
        try:
            _items = [
                'data'
            ]
            _dataHandle = dataHandle(_items, datas)
            _data = _dataHandle.datas['data'][0].split(' ')
            if _data[1] == '1':
                rl.append((_date, 1))
        except Exception as e:
            logging.error(e)

    def _handleTxt_selfCheckLog(self, datas, rl):
        logging.debug('> _handleTxt_selfCheckLog')

        """
        处理自检日志
        """
        try:
            _items = [
                'checktime',
                'errortype',
                'errorcontent',
                'errorlevel',
                'hardcode',
                'hardstatus',
                'warninglevel'
            ]
            _dataHandle = dataHandle(_items, datas)
            _tmp_1 = []
            _tmp_2 = []
            for _item in _dataHandle.datas['errorlevel']:
                _index = _dataHandle.datas['errorlevel'].index(_item)
                if _item == '1':
                    _tmp_1.append(_dataHandle.datas['errortype'][_index])
                elif _item == '2':
                    _tmp_2.append(_dataHandle.datas['errortype'][_index])
            _date = self.time2str(self.str2time(_dataHandle.datas['checktime'][0]), mode=GET_TYPE_DIGITLE)
            _SERIAL_1 = _tmp_1.count('2')
            _SERIAL_2 = _tmp_2.count('2')
            _LL_1 = _tmp_1.count('101')
            _LL_2 = _tmp_2.count('101')
            _RL_1 = _tmp_1.count('102')
            _RL_2 = _tmp_1.count('102')
            _SYS_1 = _tmp_1.count('201')
            _SYS_2 = _tmp_2.count('201')

            rr = [
                _date,
                _SERIAL_1,
                _SERIAL_2,
                _LL_1,
                _LL_2,
                _RL_1,
                _RL_2,
                _SYS_1,
                _SYS_2
            ]
            rl.append(rr)
        except Exception as e:
            logging.error(e)


    def _handleTxt_2d(self, datas):
        logging.debug('> _handleTxt_2d')
        """
        处理2DLOG
        """
        _return = None
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'index',
                'widthmeas',
                'heightmeas',
                'sectioncount'
            ]
            _dataHandle = dataHandle(_items, datas)
        except Exception as e:
            logging.error(e)

        finally:
            return _return

    def _handleTxt_3d(self, datas, l):
        logging.debug('> _handleTxt_3d')
        """
        处理3D成像数据
        """
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'index',
                'widthmeas',
                'heightmeas',
                'sectioncount'
            ]
            _dataHandle = dataHandle(_items, datas).datas
            l.append(_dataHandle)
        except Exception as e:
            logging.error(e)
            
    def _handleTxt_3dlog(self, datas, l):
        logging.debug('> _handleTxt_3dlog')
        """
        处理3D成像数据
        """
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'startbit_time',
                'startbit',
                'starttime_time',
                'starttime',
                'index_time',
                'index',
                'sectioncount_time',
                'sectioncount',
                'cxtype_time',
                'cxtype',
                'isError_time',
                'isError',
                'endtime_time',
                'endtime',
                'endbit_time',
                'endbit'
            ]
            _dataHandle = dataHandle(_items, datas).datas
            for i in _dataHandle['starttime']:
                s = self.str2time(i)
                index = _dataHandle['starttime'].index(i)
                e = self.str2time(_dataHandle['endtime'][index])
                diff = (e-s).seconds
                l.append(diff)
        except Exception as e:
            logging.error(e)

    
    def _handleTxt_slant(self, datas):
        logging.debug('> _handleTxt_slant')
        """
        处理报警车数据
        """
        _return = None
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'index',
                'limitpart',
                'measurevalue',
                'limitlevel',
                'maxx',
                'maxy',
                'maxz',
                'carscantimes',
                'limitscantimes',
                'limitmeasureindex'
            ]
            _tmp = dataHandle(_items, datas)
            _dataHandle = _tmp.datas
            _return = _dataHandle['index']
        except Exception as e:
            logging.error(e)

        finally:
            return _return
    
        
    def _handleTxt_measuredData(self, datas):
        logging.debug('> _handleTxt_measuredData')
        """
        处理测量数据
        """
        _return = None
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'index',
                'leftWidthMeas',
                'leftWidthStad',
                'leftDownSlantHeightMeas',
                'leftDownSlantHeightStad',
                'leftUpSlantHeightMeas',
                'leftUpSlantHeightStad',
                'rightWidthMeas',
                'rightWidthStad',
                'rightDownSlantHeightMeas',
                'rightDownSlantHeightStad',
                'rightUpSlantHeightMeas',
                'rightUpSlantHeightStad',
                'heightMeas',
                'heightStad'                
            ]
            _dataHandle = dataHandle(_items, datas)
        except Exception as e:
            logging.error(e)

        
        
    def _handleTxt_indexInfo(self, datas, listproxy=None, returnItem='all'):
        logging.debug('> _handleTxt_indexInfo')
        """
        处理index文件
        """
        try:
            if datas is None:
                raise Exception('data is none')
            
            _datas = datas[1:]
            _items = [
                'logtime',
                'speed',
                'leftlimit',
                'rightlimit',
                'heightlimit',
                'trainno',
                'isj',
                'index'
            ]
            _tmp = dataHandle(_items, _datas)
            _dataHandle = _tmp.datas
            if returnItem == 'all':
                if listproxy is not None:
                    listproxy.append(_dataHandle)
                else:
                    return _dataHandle
            else:
                for i in _dataHandle['index']:
                    if i == returnItem:
                        if listproxy is not None:
                            listproxy.append(_dataHandle['trainno'][_dataHandle['index'].index(i)])
                        else:
                            return _dataHandle['trainno'][_dataHandle['index'].index(i)]
        
        except Exception as e:
            logging.error(e)

    def _handleTxt_systemLog(self, datas, mlist=None):
        logging.debug('> _handleTxt_systemLog')
        """
        处理系统日志
        """
        try:
            if datas is None:
                raise Exception('data is none')
            _items = [
                'logtime',
                'errortype',
                'errorcontent',
                'errorlevel',
                'warninglevel'
            ]
            _dataHandle = dataHandle(_items, datas)
            _sys_succeed = 0
            _sys_fail = 0
            for _item in _dataHandle.datas['errortype']:
                """
                开始处理数据
                """
                if _item == '301':
                    _sys_succeed += 1
                if _item == '302':
                    _sys_fail += 1

            if mlist is not None:
                mlist.append((_sys_succeed, _sys_fail))
            else:
                return _dataHandle.datas
        except Exception as e:
            logging.error(e)



class Ui_MainWindow(PySide.QtGui.QWidget):
# class Ui_MainWindow(PySide.QtGui.QMainWindow):
    """
    主窗体
    """
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(600, 453)
        MainWindow.setFixedSize(600, 453)
        # MainWindow.setWindowFlags(PySide.QtCore.Qt.FramelessWindowHint)
        self.centralwidget = PySide.QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.btnStart = PySide.QtGui.QPushButton(self.centralwidget)
        self.btnStart.setGeometry(PySide.QtCore.QRect(210, 375, 181, 31))
        self.btnStart.setObjectName("btnStart")
        self.trShow = PySide.QtGui.QTreeWidget(self.centralwidget)
        self.trShow.setGeometry(PySide.QtCore.QRect(10, 40, 581, 331))
        self.trShow.setColumnCount(2)
        self.trShow.setObjectName("trShow")
        self.trShow.setColumnWidth(0, 190)
        self.trShow.setColumnWidth(1, 250)
        self.fillQTree(itemsMainwindow)
        self.trShow.setItemsExpandable(False)
        self.trShow.expandAll()
        today = PySide.QtCore.QDate.currentDate()
        self.startDate = PySide.QtGui.QDateTimeEdit(self.centralwidget)
        self.startDate.setGeometry(PySide.QtCore.QRect(90, 10, 194, 22))
        self.startDate.setObjectName("startDate")
        _startDate = today.addDays(-30)
        self.startDate.setDate(_startDate)
        self.endDate = PySide.QtGui.QDateTimeEdit(self.centralwidget)
        self.endDate.setGeometry(PySide.QtCore.QRect(385, 10, 194, 22))
        _endDate = today.addDays(1)
        self.endDate.setObjectName("endDate")
        self.endDate.setDate(_endDate)
        self.label = PySide.QtGui.QLabel(self.centralwidget)
        self.label.setGeometry(PySide.QtCore.QRect(20, 10, 54, 20))
        self.label.setObjectName("label")
        self.label_2 = PySide.QtGui.QLabel(self.centralwidget)
        self.label_2.setGeometry(PySide.QtCore.QRect(317, 11, 54, 20))
        self.label_2.setObjectName("label_2")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = PySide.QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(PySide.QtCore.QRect(0, 0, 600, 23))
        self.menubar.setObjectName("menubar")
        self.menu = PySide.QtGui.QMenu(self.menubar)
        self.menu.setObjectName("menu")
        MainWindow.setMenuBar(self.menubar)
        
        self.statusbar = PySide.QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOptions = PySide.QtGui.QAction(MainWindow)
        self.actionOptions.setObjectName("actionOptions")
        self.menu.addAction(self.actionOptions)
        self.menubar.addAction(self.menu.menuAction())

        self.connect(self.actionOptions, PySide.QtCore.SIGNAL("triggered()"), self.showSettingWindows)
        self.retranslateUi(MainWindow)
        self.connect(self.btnStart, PySide.QtCore.SIGNAL('clicked()'), self.Start)
        PySide.QtCore.QMetaObject.connectSlotsByName(MainWindow)


    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(PySide.QtGui.QApplication.translate("MainWindow", "验证工具", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.btnStart.setText(PySide.QtGui.QApplication.translate("MainWindow", "开始", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.trShow.headerItem().setText(0, PySide.QtGui.QApplication.translate("MainWindow", "验证项", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.trShow.headerItem().setText(1, PySide.QtGui.QApplication.translate("MainWindow", "结果", None, PySide.QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.trShow.isSortingEnabled()
        self.trShow.setSortingEnabled(False)
        self.trShow.setSortingEnabled(__sortingEnabled)
        self.label.setText(PySide.QtGui.QApplication.translate("MainWindow", "开始时间", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(PySide.QtGui.QApplication.translate("MainWindow", "结束时间", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.menu.setTitle(PySide.QtGui.QApplication.translate("MainWindow", "设置", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.actionOptions.setText(PySide.QtGui.QApplication.translate("MainWindow", "验证参数", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self._logic = logic()
        
    def fillQTree(self, items):
        itemslist = ['设备状态检查', '数据质量检查', '测量性能验证']
        for key in itemslist:
            item_0 = PySide.QtGui.QTreeWidgetItem(self.trShow)
            i_index = itemslist.index(key)
            self.trShow.topLevelItem(i_index).setText(0, PySide.QtGui.QApplication.translate("uiSetting", key, None, PySide.QtGui.QApplication.UnicodeUTF8))
            for i in items[key]:
                ii_index = items[key].index(i)
                item_1 = PySide.QtGui.QTreeWidgetItem(item_0)
                item_1.setFlags(PySide.QtCore.Qt.ItemIsSelectable|PySide.QtCore.Qt.ItemIsEnabled)
                self.trShow.topLevelItem(i_index).child(ii_index).setText(0, PySide.QtGui.QApplication.translate("uiSetting", i, None, PySide.QtGui.QApplication.UnicodeUTF8))
        
    def showSettingWindows(self):
        _widget = PySide.QtGui.QDialog()
        settingWnd = Ui_SettingWindow()
        settingWnd.setupUi(_widget)
        _widget.exec_()
        
    def Start(self):        
        m = multiprocessing.Manager()
        p_result = m.Queue()
        logging.info('进程管理线程启动 > ')

        _tDo = threading.Thread(
            target=self._logic._start, 
            args=(
                self.startDate.dateTime().toPython(), 
                self.endDate.dateTime().toPython(),
                p_result
                )
            )
        _tDo.start()
        logging.info('监控线程启动 > ')        
        _t = threading.Thread(
            target=self.monitor, 
            args=(p_result,)
        )
        # _t.daemon = True
        _t.start()
    
    def monitor(self, q):
        _r = None
        while 1:
            try:
                if not q.empty():
                    _r = q.get_nowait()
                    #logging.debug(_r)
                    self.trShow.topLevelItem(_r[0]).child(_r[1]).setText(1, PySide.QtGui.QApplication.translate("MainWindow", str(_r[2]), None, PySide.QtGui.QApplication.UnicodeUTF8))
            except Exception as e:
                logging.error(e)
                break
                
class Ui_SettingWindow(PySide.QtCore.QObject):
    def setupUi(self, uiSetting):
        self.ui = uiSetting
        self.lastOpen = None
        self.enableEdit = [1]
        uiSetting.setObjectName("uiSetting")
        uiSetting.resize(400, 341)
        self.treeWidget = PySide.QtGui.QTreeWidget(uiSetting)
        self.treeWidget.setGeometry(PySide.QtCore.QRect(10, 10, 381, 281))
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setColumnWidth(0, 150)
        self.treeWidget.setColumnWidth(1, 200)
        self.fillQTree(itemsSettting)
        self.treeWidget.setItemsExpandable(False)
        self.treeWidget.expandAll()
        
        
        self.horizontalLayoutWidget = PySide.QtGui.QWidget(uiSetting)
        self.horizontalLayoutWidget.setGeometry(PySide.QtCore.QRect(10, 290, 381, 51))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = PySide.QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnSave = PySide.QtGui.QPushButton(self.horizontalLayoutWidget)
        self.btnSave.setObjectName("btnSave")
        self.horizontalLayout.addWidget(self.btnSave)
        self.btnClose = PySide.QtGui.QPushButton(self.horizontalLayoutWidget)
        self.btnClose.setObjectName("btnClose")
        self.horizontalLayout.addWidget(self.btnClose)
        
        self.connect(self.treeWidget, PySide.QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *, int)'), self.trDbClicked)
        self.connect(self.treeWidget, PySide.QtCore.SIGNAL('itemSelectionChanged()'), self.trSelectChg)
        self.btnSave.clicked.connect(self._save)
        self.retranslateUi(uiSetting)
        self.connect(self.btnClose, PySide.QtCore.SIGNAL('clicked()'), self._close)
        PySide.QtCore.QMetaObject.connectSlotsByName(uiSetting)


    def fillQTree(self, items):
        for key in items.keys():
            item_0 = PySide.QtGui.QTreeWidgetItem(self.treeWidget)
            i_index = list(items.keys()).index(key)
            self.treeWidget.topLevelItem(i_index).setText(0, PySide.QtGui.QApplication.translate("uiSetting", key, None, PySide.QtGui.QApplication.UnicodeUTF8))
            for i in items[key]:
                ii_index = items[key].index(i)
                item_1 = PySide.QtGui.QTreeWidgetItem(item_0)
                item_1.setFlags(PySide.QtCore.Qt.ItemIsSelectable|PySide.QtCore.Qt.ItemIsEnabled)
                self.treeWidget.topLevelItem(i_index).child(ii_index).setText(0, PySide.QtGui.QApplication.translate("uiSetting", i, None, PySide.QtGui.QApplication.UnicodeUTF8))
                try:
                    _text = _vt_conf.config.get(key, i)
                except:
                    _text = ''
                
                self.treeWidget.topLevelItem(i_index).child(ii_index).setText(1, PySide.QtGui.QApplication.translate("uiSetting", _text, None, PySide.QtGui.QApplication.UnicodeUTF8))


    def _save(self):
        topCount = self.treeWidget.topLevelItemCount()
        saved = []
        for i in range(topCount):
            _item = self.treeWidget.topLevelItem(i)
            if _item.childCount() <= 0: continue
            for j in range(_item.childCount()):
                _child = _item.child(j)
                saved.append((_item.text(0), _child.text(0), _child.text(1)))
        _vt_conf.saveConfig(saved)
        self.ui.close()
        
    def _close(self):
        self.ui.close()
        
    def trDbClicked(self, item, col):
        if col in self.enableEdit:
            self.treeWidget.openPersistentEditor(item, col)
            self.lastOpen = item
    
    def trSelectChg(self):
        self.treeWidget.closePersistentEditor(self.lastOpen, 1)
        self.lastOpen = None
    
    def retranslateUi(self, uiSetting):
        uiSetting.setWindowTitle(PySide.QtGui.QApplication.translate("uiSetting", "参数设置", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(0, PySide.QtGui.QApplication.translate("uiSetting", "参数名称", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(1, PySide.QtGui.QApplication.translate("uiSetting", "参数值", None, PySide.QtGui.QApplication.UnicodeUTF8))
        __sortingEnabled = self.treeWidget.isSortingEnabled()
        self.treeWidget.setSortingEnabled(False)
        self.treeWidget.setSortingEnabled(__sortingEnabled)
        self.btnSave.setText(PySide.QtGui.QApplication.translate("uiSetting", "保存", None, PySide.QtGui.QApplication.UnicodeUTF8))
        self.btnClose.setText(PySide.QtGui.QApplication.translate("uiSetting", "关闭", None, PySide.QtGui.QApplication.UnicodeUTF8))

class MainWindow(PySide.QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):  
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

    def closeEvent(self, event):
        # print(dir(event))
        import subprocess
        cmds = ['taskkill', '/im', sys.argv[0][sys.argv[0].rfind(os.sep)+1:], '-f']
        subprocess.call(cmds)

def test():
    _logic = logic()
    f = r'D:\gqpics\202.202.202.2\20170809062732\index.txt'
    _data = TxtReader(f)
    print(_data.data)


def Go():
    app = PySide.QtGui.QApplication(sys.argv)
    mainWnd = MainWindow()
    mainWnd.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    # test()
    multiprocessing.freeze_support()
    if hasattr(sys, 'frozen'):
        os.putenv('_MEIPASS2', sys._MEIPASS)

    Go()
    
