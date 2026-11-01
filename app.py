"""
Tampilan Utama (Streamlit UI) - Puzzle World
Mengimpor modul:
- puzzle_generator.py (Tahap 1: Pembuat bingkai & potongan teka-teki)
- puzzle_solver.py    (Tahap 2: Penyusun kembali potongan menjadi citra utuh)
"""
import io
import os
import sys
import time
import zipfile
import subprocess
import numpy as np
import streamlit as st
from PIL import Image
from streamlit.runtime.scriptrunner import get_script_run_ctx

if __name__ == "__main__" and get_script_run_ctx(suppress_warning=True) is None:
    subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

from puzzle_generator import buat_puzzle
from puzzle_solver import solve_puzzle

OUT_DIR = "output"
PIECES_DIR = os.path.join(OUT_DIR, "pieces")

st.set_page_config(page_title="Puzzle World - PCD", layout="wide")
S = st.session_state


# ==============================================================================
# FUNGSI PEMANGGIL GENERATOR
# ==============================================================================
def jalankan_generator(img_pil, M, margin_rasio, rotasi_acak, acak_urutan):
    """Memanggil modul puzzle_generator dan menyimpan state beserta file unduhan ke aplikasi."""
    frame, pot_list, info = buat_puzzle(
        img_pil=img_pil,
        M=M,
        margin_rasio=margin_rasio,
        rotasi_acak=rotasi_acak,
        acak_urutan=acak_urutan,
        out_dir=OUT_DIR
    )
    S.frame = frame
    S.pot = pot_list
    S.info = info

    # Siapkan buffer ZIP paket lengkap (frame.png + pieces/piece_XX.png)
    buf_frame = io.BytesIO()
    Image.fromarray(frame).save(buf_frame, format="PNG")

    buf_all_zip = io.BytesIO()
    with zipfile.ZipFile(buf_all_zip, "w", zipfile.ZIP_DEFLATED) as za:
        za.writestr("frame.png", buf_frame.getvalue())
        for pot, nama in zip(pot_list, info["nama_files"]):
            b_pot = io.BytesIO()
            Image.fromarray(pot).save(b_pot, format="PNG")
            za.writestr(f"pieces/{nama}", b_pot.getvalue())

    S.all_zip_bytes = buf_all_zip.getvalue()


# ==============================================================================
# SIDEBAR: PARAMETER GENERATOR
# ==============================================================================
with st.sidebar:
    st.title("🧩 Puzzle World")
    st.caption("Tugas Besar Pengolahan Citra Digital")

    st.subheader("1. Unggah Gambar (Generator)")
    uploaded_file = st.file_uploader(
        "Pilih citra utuh (RGB / Grayscale)",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        key="gen_uploader"
    )

    st.subheader("2. Parameter Generator")
    M_input = st.slider("Ukuran Grid (M × M)", min_value=2, max_value=8, value=4)
    margin_input = st.slider("Rasio Margin Bingkai", min_value=0.01, max_value=0.25, value=0.07, step=0.01)
    rotasi_input = st.checkbox("Rotasi Acak (0°/90°/180°/270°)", value=True)
    acak_input = st.checkbox("Acak Urutan Potongan", value=True)

    tombol_acak_ulang = st.button(
        "🔀 Buat / Acak Ulang Puzzle",
        disabled=uploaded_file is None,
        use_container_width=True
    )


# Jalankan Generator HANYA saat gambar/parameter berubah atau tombol acak ulang diklik
if uploaded_file is not None:
    config_sekarang = (uploaded_file.name, uploaded_file.size, M_input, margin_input, rotasi_input, acak_input)
    if S.get("config_aktif") != config_sekarang or tombol_acak_ulang:
        img_in = Image.open(uploaded_file)
        jalankan_generator(img_in, M_input, margin_input, rotasi_input, acak_input)
        S.config_aktif = config_sekarang


# ==============================================================================
# LAYAR UTAMA: 2 TAB (TAHAP 1: PUZZLE GENERATOR | TAHAP 2: PUZZLE SOLVER)
# ==============================================================================
st.header("🧩 Puzzle World — Generator & Solver (PCD)")

tab_gen, tab_solver = st.tabs([
    "🛠️ Tahap 1: Puzzle Generator",
    "🤖 Tahap 2: Puzzle Solver Otomatis (1 Bingkai + N Potongan)"
])

# ------------------------------------------------------------------------------
# TAB 1: PUZZLE GENERATOR
# ------------------------------------------------------------------------------
with tab_gen:
    if "info" not in S:
        st.info(
            "👈 Silakan unggah gambar utuh pada sidebar di sebelah kiri untuk membuat bingkai & potongan puzzle, "
            "atau buka tab **🤖 Tahap 2: Puzzle Solver Otomatis** jika Anda ingin langsung mengunggah 1 bingkai dan N potongan."
        )
    else:
        info = S.info
        M = info["M"]
        N = M * M
        W, H = info["ukuran_asli"]

        st.success(
            f"✅ Puzzle berhasil dibuat! Bingkai disimpan di `{OUT_DIR}/frame.png` dan **{N} potongan** disimpan di `{PIECES_DIR}/`."
        )
        st.caption(
            f"Ukuran citra: **{W} × {H} px** | Mode: **{info.get('mode', 'RGB')}** | "
            f"Grid: **{M} × {M} ({N} potongan)**"
        )

        st.download_button(
            label="🗂️ Unduh Hasil Generator (Bingkai + Potongan .zip)",
            data=S.all_zip_bytes,
            file_name="puzzle_output.zip",
            mime="application/zip",
            use_container_width=True
        )

        kiri, kanan = st.columns([1, 1.3])

        with kiri:
            st.subheader("Citra Bingkai (frame.png)")
            st.image(S.frame, caption=f"{OUT_DIR}/frame.png", use_container_width=True)

        with kanan:
            st.subheader(f"Hasil Potongan Puzzle ({N} Potongan)")
            kol = st.columns(min(4, max(1, M)))
            for i, (pot, nama) in enumerate(zip(S.pot, info["nama_files"])):
                with kol[i % len(kol)]:
                    st.image(pot, caption=nama, use_container_width=True)


# ------------------------------------------------------------------------------
# TAB 2: PUZZLE SOLVER OTOMATIS (INPUT MANUAL: 1 CITRA BINGKAI + N POTONGAN CITRA)
# ------------------------------------------------------------------------------
with tab_solver:
    st.subheader("Tahap 2: Puzzle Solver Otomatis")
    st.markdown(
        "Modul ini menerima unggahan **1 citra bingkai** dan **N potongan citra**, "
        "mendeteksi area kosong pada bingkai, lalu merangkai kembali seluruh potongan beserta rotasinya "
        "menjadi citra utuh menggunakan analisis kontinuitas piksel dan gradien tepi (PCD)."
    )

    frame_solver = None
    pieces_solver = []
    nama_pieces_solver = []

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        up_frame = st.file_uploader(
            "1. Unggah 1 Citra Bingkai (frame.png)",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
            key="solver_frame_up"
        )
    with col_up2:
        up_pieces = st.file_uploader(
            "2. Unggah N Potongan Citra (pilih semua file piece_XX.png)",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
            accept_multiple_files=True,
            key="solver_pieces_up"
        )

    if up_frame is not None and up_pieces:
        img_f = Image.open(up_frame)
        if img_f.mode not in ("RGB", "L"):
            img_f = img_f.convert("RGB")
        frame_solver = np.array(img_f)

        up_pieces_sorted = sorted(up_pieces, key=lambda f: f.name)
        for pf in up_pieces_sorted:
            im_p = Image.open(pf)
            if im_p.mode not in ("RGB", "L"):
                im_p = im_p.convert("RGB")
            pieces_solver.append(np.array(im_p))
            nama_pieces_solver.append(pf.name)

        st.info(f"Masukan diterima: **1 Bingkai** (`{up_frame.name}`) dan **{len(pieces_solver)} Potongan Citra**.")

    if frame_solver is not None and len(pieces_solver) > 0:
        with st.expander("👁️ Lihat Masukan (1 Citra Bingkai & N Potongan)", expanded=False):
            c_in1, c_in2 = st.columns([1, 1.5])
            with c_in1:
                st.image(frame_solver, caption="Citra Bingkai Masukan", use_container_width=True)
            with c_in2:
                n_p = len(pieces_solver)
                cols_p = st.columns(min(6, max(1, n_p)))
                for idx_p, (im_p, nm_p) in enumerate(zip(pieces_solver, nama_pieces_solver)):
                    with cols_p[idx_p % len(cols_p)]:
                        st.image(im_p, caption=nm_p, use_container_width=True)

        if st.button("🚀 Jalankan Puzzle Solver (Rangkai Citra Utuh)", type="primary", use_container_width=True):
            try:
                t_mulai = time.time()
                with st.spinner("Menganalisis tepi piksel & merangkai potongan puzzle..."):
                    hasil_citra, board_sol, detail_sol, area_sol = solve_puzzle(frame_solver, pieces_solver)
                durasi = time.time() - t_mulai

                os.makedirs(OUT_DIR, exist_ok=True)
                solved_path = os.path.join(OUT_DIR, "solved.png")
                Image.fromarray(hasil_citra).save(solved_path)

                S.solver_result = {
                    "frame": frame_solver,
                    "hasil": hasil_citra,
                    "detail": detail_sol,
                    "area": area_sol,
                    "nama_pieces": nama_pieces_solver,
                    "durasi": durasi,
                    "M": int(round(np.sqrt(len(pieces_solver))))
                }
            except Exception as e:
                st.error(f"Gagal menyusun puzzle: {e}")

    if S.get("solver_result") is not None:
        res = S.solver_result
        st.divider()
        st.success(
            f"✅ Puzzle berhasil dirangkai menjadi citra utuh dalam **{res['durasi']:.2f} detik**! "
            f"(Area bingkai terdeteksi: `x={res['area']['x0']}..{res['area']['x1']}`, `y={res['area']['y0']}..{res['area']['y1']}`)"
        )

        col_out1, col_out2 = st.columns(2)
        with col_out1:
            st.subheader("Input: Citra Bingkai")
            st.image(res["frame"], caption="1 Citra Bingkai + Area Kosong", use_container_width=True)
        with col_out2:
            st.subheader("Luaran: Citra Utuh Hasil Rangkaian")
            st.image(res["hasil"], caption="Citra Utuh Hasil Puzzle Solver (output/solved.png)", use_container_width=True)

        buf = io.BytesIO()
        Image.fromarray(res["hasil"]).save(buf, format="PNG")
        st.download_button(
            label="💾 Unduh Citra Utuh (solved.png)",
            data=buf.getvalue(),
            file_name="solved.png",
            mime="image/png",
            use_container_width=True
        )

        with st.expander("📋 Detail Penempatan & Rotasi Setiap Slot", expanded=False):
            M_sol = res["M"]
            for r in range(M_sol):
                cols_d = st.columns(M_sol)
                for c in range(M_sol):
                    slot_idx = r * M_sol + c
                    d = res["detail"][slot_idx]
                    nm = res["nama_pieces"][d["idx_potongan"]]
                    with cols_d[c]:
                        st.markdown(
                            f"**Slot {slot_idx + 1}** `(Baris {r}, Kolom {c})`  \n"
                            f"📄 `{nm}`  \n"
                            f"🔄 Putar balik: `{d['derajat_putar']}°` CCW"
                        )
