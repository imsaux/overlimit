# -*- mode: python -*-

block_cipher = None


a = Analysis(['vt.py'],
             pathex=['c:\\python34', 'D:\\codes\\p\\OverLimit', 'c:\\python34\\scripts'],
             binaries=[],
             datas=[],
             hiddenimports=['ctypes','uuid', 'decimal', 'xml.etree.ElementTree', 'PySide.QtCore', 'PySide.QtGui', 'pymssql', '_mssql', 'multiprocessing'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='vt',
          debug=False,
          strip=False,
          upx=False,
          console=False )
