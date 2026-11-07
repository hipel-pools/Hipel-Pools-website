#!/usr/bin/env python3
"""
Download every HubSpot-hosted file the site references (src/data/images.json)
into public/<local path>, shrinking oversized photos so pages load fast.

Usage: python3 -I scripts/migrate/download_files.py <repo-root>
Re-running skips files that already exist.
"""
import json, os, sys, ssl, urllib.request, concurrent.futures, io

ROOT = sys.argv[1]
MAX_W = 2400
files = json.load(open(os.path.join(ROOT, 'src/data/images.json')))
ctx = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE', '/root/.ccr/ca-bundle.crt')) \
    if os.path.exists('/root/.ccr/ca-bundle.crt') else ssl.create_default_context()

try:
    from PIL import Image
except ImportError:
    Image = None


def shrink(data, ext):
    if Image is None or ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return data
    try:
        im = Image.open(io.BytesIO(data))
        if im.width <= MAX_W and len(data) < 600_000:
            return data
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        out = io.BytesIO()
        if ext in ('.jpg', '.jpeg'):
            im.convert('RGB').save(out, 'JPEG', quality=82, optimize=True, progressive=True)
        elif ext == '.png':
            im.save(out, 'PNG', optimize=True)
        else:
            im.save(out, 'WEBP', quality=82)
        return out.getvalue() if out.tell() < len(data) else data
    except Exception:
        return data


def get(item):
    src, loc = item
    dest = os.path.join(ROOT, 'public', loc.lstrip('/'))
    if os.path.exists(dest):
        return 'skip', src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0 site-migration'})
        data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
    except Exception as e:
        return 'fail %s' % e, src
    data = shrink(data, os.path.splitext(dest)[1].lower())
    if src.lower().endswith('.mov') and dest.endswith('.mp4'):
        tmp = dest + '.mov'
        open(tmp, 'wb').write(data)
        transcode(tmp, dest)
        os.remove(tmp)
    else:
        open(dest, 'wb').write(data)
    if dest.endswith('.mp4'):
        poster(dest)
    return 'ok', src


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return 'ffmpeg'


def transcode(src, dest):
    import subprocess
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', src, '-vf', "scale='min(1920,iw)':-2", '-c:v', 'libx264',
                    '-crf', '28', '-preset', 'slow', '-an', '-movflags', '+faststart', dest], check=True)


def poster(mp4):
    import subprocess
    out = mp4[:-4] + '-poster.jpg'
    if not os.path.exists(out):
        subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-ss', '2', '-i', mp4, '-frames:v', '1',
                        '-vf', "scale='min(1280,iw)':-2", '-q:v', '4', out], check=False)


with concurrent.futures.ThreadPoolExecutor(12) as ex:
    res = list(ex.map(get, files.items()))
for root, _, fs in os.walk(os.path.join(ROOT, 'public/files')):
    for f in fs:
        if f.endswith('.mp4'):
            poster(os.path.join(root, f))
fails = [r for r in res if r[0].startswith('fail')]
print('ok', sum(r[0] == 'ok' for r in res), 'skipped', sum(r[0] == 'skip' for r in res), 'failed', len(fails))
for f in fails:
    print(' ', f[0], f[1])
