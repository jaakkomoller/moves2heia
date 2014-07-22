# -*- mode: python -*-
a = Analysis(['moves2heia.py'],
             pathex=['c:\\Users\\Maria\\Downloads\\moves2heia'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
a.zipfiles.append(("poster", "C:\Users\Maria\Downloads\poster-0.8.1-py2.7.egg", "BINARY"))
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='moves2heia.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
