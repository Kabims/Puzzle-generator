"""
Modul 1: Puzzle Generator
Bertugas membaca citra masukan, membuat bingkai (frame), memotong area kosong
menjadi M x M potongan, melakukan rotasi/pengacakan opsional, dan menyimpan keluaran.
"""
import os
import glob
import json
import random
import numpy as np
from PIL import Image


def buat_bingkai(arr, margin_rasio=0.07):
    """Membuat citra bingkai dengan bagian tengah dikosongkan (putih = 255)."""
    H, W = arr.shape[:2]
    mx, my = int(round(W * margin_rasio)), int(round(H * margin_rasio))
    frame = arr.copy()
    frame[my:H - my, mx:W - mx] = 255
    area = dict(x0=mx, y0=my, x1=W - mx, y1=H - my)
    return frame, area


def potong_grid(arr, M, area):
    """Memotong area kosong pada bingkai menjadi M x M potongan."""
    x0, y0, x1, y1 = area["x0"], area["y0"], area["x1"], area["y1"]
    ys = np.linspace(y0, y1, M + 1).astype(int)
    xs = np.linspace(x0, x1, M + 1).astype(int)
    pieces = []
    for r in range(M):
        for c in range(M):
            p = arr[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].copy()
            pieces.append(dict(
                row=r,
                col=c,
                img=p,
                box=(int(xs[c]), int(ys[r]), int(xs[c + 1]), int(ys[r + 1]))
            ))
    return pieces


def buat_puzzle(img_pil, M=4, margin_rasio=0.07, rotasi_acak=True, acak_urutan=True, out_dir="output"):
    """
    Memproses citra masukan menjadi bingkai & N potongan puzzle,
    menyimpan hasilnya ke folder `out_dir`, serta mengembalikan:
    (arr_asli, frame, pot_list, kunci)
    """
    if img_pil.mode not in ("RGB", "L"):
        img_pil = img_pil.convert("RGB")

    arr = np.array(img_pil)
    H, W = arr.shape[:2]
    N = M * M

    frame, area = buat_bingkai(arr, margin_rasio)
    pieces = potong_grid(arr, M, area)

    for p in pieces:
        k = random.randint(0, 3) if rotasi_acak else 0
        p["rot"] = k * 90
        if k:
            p["img"] = np.rot90(p["img"], k).copy()

    urutan = list(range(N))
    if acak_urutan:
        random.shuffle(urutan)

    pieces_dir = os.path.join(out_dir, "pieces")
    os.makedirs(pieces_dir, exist_ok=True)
    for old_file in glob.glob(os.path.join(pieces_dir, "piece_*.png")):
        try:
            os.remove(old_file)
        except OSError:
            pass

    Image.fromarray(frame).save(os.path.join(out_dir, "frame.png"))

    kunci = {
        "M": M,
        "ukuran_asli": [W, H],
        "mode": img_pil.mode,
        "area_bingkai": area,
        "potongan": []
    }
    pot_list = []

    for nomor, idx in enumerate(urutan):
        p = pieces[idx]
        nama = f"piece_{nomor:02d}.png"
        Image.fromarray(p["img"]).save(os.path.join(pieces_dir, nama))
        pot_list.append(p["img"])
        kunci["potongan"].append({
            "file": nama,
            "baris_asli": p["row"],
            "kolom_asli": p["col"],
            "posisi_di_bingkai_xyxy": p["box"],
            "rotasi_derajat": p["rot"]
        })

    with open(os.path.join(out_dir, "kunci_jawaban.json"), "w") as f:
        json.dump(kunci, f, indent=2)

    return arr, frame, pot_list, kunci
