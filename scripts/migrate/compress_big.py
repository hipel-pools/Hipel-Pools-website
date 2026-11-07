#!/usr/bin/env python3
"""Shrink oversized PDFs (re-encode embedded images) and MP4s (H.264 720p) under public/files.
Usage: python3 -I scripts/migrate/compress_big.py <repo-root>   (needs: pip install pikepdf imageio-ffmpeg)"""
import os, sys, io, subprocess, glob
ROOT = sys.argv[1]
LIMIT = 15 * 1024 * 1024

def pdf(path):
    import pikepdf
    from PIL import Image
    from pikepdf import PdfImage
    pdf = pikepdf.open(path)
    for page in pdf.pages:
        for name, raw in list(page.images.items()):
            try:
                pim = PdfImage(raw)
                im = pim.as_pil_image()
                if im.mode not in ('RGB', 'L'):
                    im = im.convert('RGB')
                if max(im.size) > 2000:
                    im.thumbnail((2000, 2000), Image.LANCZOS)
                buf = io.BytesIO(); im.save(buf, 'JPEG', quality=72, optimize=True)
                raw.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
                raw.Width, raw.Height = im.size
                raw.ColorSpace = pikepdf.Name.DeviceRGB if im.mode == 'RGB' else pikepdf.Name.DeviceGray
                raw.BitsPerComponent = 8
                for k in ('/DecodeParms', '/SMask', '/Mask', '/Decode'):
                    if k in raw and k != '/SMask':
                        del raw[k]
            except Exception as e:
                print('   skip image', name, e)
    tmp = path + '.tmp'
    pdf.save(tmp, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    pdf.close()
    os.replace(tmp, path)

def mp4(path):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe(); tmp = path + '.tmp.mp4'
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', path, '-vf', "scale='min(1280,iw)':-2", '-c:v', 'libx264',
                    '-crf', '28', '-preset', 'slow', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, path)

for f in glob.glob(os.path.join(ROOT, 'public/files/**/*'), recursive=True):
    if os.path.isfile(f) and os.path.getsize(f) > LIMIT:
        before = os.path.getsize(f)
        (pdf if f.lower().endswith('.pdf') else mp4 if f.lower().endswith('.mp4') else (lambda p: None))(f)
        print('%s %.1fMB -> %.1fMB' % (os.path.basename(f), before / 1048576, os.path.getsize(f) / 1048576))
