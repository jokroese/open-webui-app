from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('cv2', include_py_files=False)