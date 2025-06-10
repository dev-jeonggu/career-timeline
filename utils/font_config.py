import matplotlib
import matplotlib.font_manager as fm
import platform
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
matplotlib.rcParams['axes.unicode_minus'] = False

def set_korean_font():
    if platform.system() == 'Darwin':
        matplotlib.rcParams['font.family'] = 'AppleGothic'
    elif platform.system() == 'Linux':
        font_names = [font.name for font in fm.fontManager.ttflist]
        for font in ['NanumGothic', 'NanumBarunGothic', 'DejaVu Sans']:
            if font in font_names:
                matplotlib.rcParams['font.family'] = font
                break
