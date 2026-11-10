import sys
from zs import unzs; from byml import Byml; from bntx import textures; from tex import decode
from PIL import Image, ImageDraw
mp = Byml(unzs('Banc/BancBasedResource/MapParam.byml.zs')).root
ci = Byml(unzs('Game/MapCaptureInfo/MapCaptureInfo.game__MapCaptureInfo.bgyml')).root['MapCaptureParamArray']
def run(tex, banc, cap, out, flip=1):
    b = unzs(f'UI/CustomTex/Map/Field/{tex}.bntx.zs'); t = textures(b)[tex]
    im = decode(b, t, True).convert('RGB'); W, H = im.size
    c = ci[cap]; cx, cz, h = c['CameraPos']['X'], c['CameraPos']['Z'], c['Height']
    s = H / h
    d = ImageDraw.Draw(im)
    col = {'CollectSignAll': 'yellow', 'TBox': 'red', 'CollectHeartAll': 'magenta', 'Facility': 'cyan', 'EntranceAnchor': 'lime'}
    for k, color in col.items():
        for e in mp[banc].get(k, []):
            x, y, z = e['Trans']; px, py = W / 2 + (x - cx) * s, H / 2 + flip * (z - cz) * s
            d.ellipse((px - 14, py - 14, px + 14, py + 14), outline=color, width=6)
    im.resize((W // 2, H // 2)).save(out)
run('KokiriForest_Child_00', 'KokiriForest_Child', 0, 'map_kokiri.png')
run('HyruleField_Child_00', 'HyruleField_Child', 9, 'map_field.png')
