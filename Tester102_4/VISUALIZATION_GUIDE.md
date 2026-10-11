# 📊 Panduan Visualisasi Data Sample

## Overview

Dokumentasi ini menjelaskan cara menggunakan tool visualisasi untuk menganalisis data sample dari Tester102_4.

## File yang Tersedia

### 1. `sample_data.csv`
File CSV yang berisi data sample terstruktur dengan kolom:
- `Sample`: Nomor sample
- `Time_s`: Waktu dalam detik
- `Position_X_m`, `Position_Y_m`: Posisi robot
- `Velocity_X_ms`, `Velocity_Y_ms`: Kecepatan
- `Speed_ms`: Kecepatan total
- `Zone`: Zona interaksi (PUBLIC, SOCIAL, PERSONAL, INTIMATE)
- `Humans_Count`: Jumlah manusia terdeteksi
- `Closest_Distance_m`: Jarak ke manusia terdekat
- `SFM_Force_X_N`, `SFM_Force_Y_N`: Gaya Social Force Model
- `Command`: Perintah gerakan
- `Displacement_X_m`, `Displacement_Y_m`: Perpindahan

### 2. `visualize_csv.py` ⭐ RECOMMENDED
Script Python untuk visualisasi komprehensif dari file CSV.

**Fitur:**
- 6 grafik berbeda dalam satu dashboard
- Statistik lengkap
- Visualisasi zona proksemik
- Vector field untuk velocity dan force
- Analisis proximity ke manusia

**Usage:**
```bash
python visualize_csv.py
```

### 3. `plot_from_samples.py`
Script yang dapat menggunakan data hardcoded atau CSV.

**Usage:**
```bash
# Gunakan CSV jika ada
python plot_from_samples.py

# Paksa gunakan data hardcoded
python plot_from_samples.py --hardcoded
```

## Grafik yang Dihasilkan

### 📍 1. Robot Trajectory Map
- Menampilkan jalur pergerakan robot
- Titik-titik diwarnai berdasarkan zona (PUBLIC=hijau, SOCIAL=kuning, PERSONAL=orange)
- Marker start (hijau) dan end (merah)
- Lingkaran zona proksemik di posisi akhir

### 🚀 2. Speed Over Time
- Grafik kecepatan robot terhadap waktu
- Background berwarna sesuai zona yang dilalui
- Area plot menunjukkan variasi kecepatan

### 👥 3. Proximity to Humans
- Jarak ke manusia terdekat
- Garis batas zona (Intimate=0.45m, Personal=1.20m, Social=3.60m)
- Area berwarna menunjukkan zona berbahaya

### ⚡ 4. Social Force Model Forces
- Magnitude gaya SFM terhadap waktu
- Menunjukkan intensitas gaya penolakan dari manusia
- Titik diwarnai sesuai zona

### 🎯 5. Velocity Vector Field
- Arrow plot menunjukkan arah dan magnitude velocity
- Diwarnai berdasarkan kecepatan (coolwarm colormap)
- Overlay pada trajectory map

### 🧲 6. SFM Force Vector Field
- Arrow plot menunjukkan arah dan magnitude gaya SFM
- Diwarnai berdasarkan magnitude force (red colormap)
- Menunjukkan bagaimana robot bereaksi terhadap manusia

## Statistik yang Ditampilkan

```
📍 Position & Movement:
   - Posisi awal dan akhir
   - Total jarak tempuh

⏱️  Time:
   - Durasi pengujian
   - Jumlah sample

🚀 Speed:
   - Rata-rata, maksimum, minimum

👥 Human Detection:
   - Jumlah sample dengan deteksi manusia
   - Jarak terdekat
   - Jarak rata-rata

🔵 Zones:
   - Distribusi waktu di setiap zona

⚡ SFM Forces:
   - Rata-rata dan maksimum magnitude

🎯 Commands:
   - Distribusi perintah gerakan
```

## Requirements

### Python Packages
```bash
pip install pandas matplotlib numpy
```

Atau gunakan file requirements yang sudah ada:
```bash
pip install -r requirements.txt
```

## Workflow Penggunaan

### Langkah 1: Export Data ke CSV
Jika Anda menjalankan `manual_camera_movement_tester.py`, data sample akan ditampilkan di terminal. Copy data tersebut dan gunakan tool untuk mengkonversi ke CSV (sudah tersedia di `sample_data.csv`).

### Langkah 2: Visualisasi
```bash
cd Tester102_4
python visualize_csv.py
```

### Langkah 3: Analisis
- Plot akan ditampilkan di window baru
- File PNG akan disimpan dengan timestamp
- Gunakan statistik di terminal untuk analisis numerik

## Tips Analisis

### 🔍 Yang Perlu Diperhatikan:

1. **Zona Transitions**
   - Perhatikan transisi antar zona di grafik Speed Over Time
   - Robot seharusnya melambat saat memasuki zona PERSONAL

2. **Force Magnitude**
   - Gaya SFM seharusnya meningkat saat mendekati manusia
   - Perhatikan arah force vector - seharusnya menjauhi manusia

3. **Closest Distance**
   - Pastikan robot tidak memasuki zona INTIMATE (<0.45m)
   - Monitor apakah ada violation

4. **Velocity Response**
   - Bandingkan velocity vector dengan force vector
   - Robot seharusnya bereaksi sesuai gaya SFM

## Troubleshooting

### Error: "File not found"
```bash
# Pastikan berada di direktori yang benar
cd Tester102_4
ls sample_data.csv
```

### Error: "Module not found"
```bash
# Install dependencies
pip install pandas matplotlib numpy
```

### Plot tidak muncul
```bash
# Cek backend matplotlib
python -c "import matplotlib; print(matplotlib.get_backend())"

# Jika perlu, install tkinter
# Windows: sudah include di Python installer
# Linux: sudo apt-get install python3-tk
```

## Output Files

Script akan menghasilkan file:
- `social_nav_analysis_YYYYMMDD_HHMMSS.png` - Dashboard lengkap
- `trajectory_plot_YYYYMMDD_HHMMSS.png` - Dari plot_from_samples.py
- `trajectory_data_YYYYMMDD_HHMMSS.csv` - Export data

## Customization

### Mengubah Zona Proksemik
Edit di bagian atas script:
```python
R_INTIMATE = 0.45  # meter
R_PERSONAL = 1.20  # meter
R_SOCIAL = 3.60    # meter
```

### Mengubah Warna Zona
```python
zone_colors = {
    'PUBLIC': 'green',
    'SOCIAL': 'yellow', 
    'PERSONAL': 'orange',
    'INTIMATE': 'red'
}
```

### Mengubah Ukuran Plot
```python
fig = plt.figure(figsize=(20, 12))  # width, height in inches
```

## Advanced Usage

### Batch Processing Multiple CSV Files
```python
import glob

csv_files = glob.glob('sample_data_*.csv')
for csv_file in csv_files:
    df = load_csv(csv_file)
    create_comprehensive_plots(df)
    plt.savefig(f'analysis_{csv_file}.png')
```

### Export to Different Formats
```python
# PDF (vector graphics)
fig.savefig('output.pdf', dpi=300)

# SVG (untuk editing)
fig.savefig('output.svg')

# High resolution PNG
fig.savefig('output.png', dpi=300)
```

## References

- Social Force Model: Helbing & Molnár (1995)
- Proxemic Zones: Hall (1966)
- Robot Navigation: ROS Navigation Stack

## Support

Untuk pertanyaan atau issue, lihat:
- `README.md` - Overview sistem
- `SAMPLING_GUIDE.md` - Panduan sampling
- `QUICK_REFERENCE.txt` - Quick commands

---

**Created:** 2026-10-06  
**Last Updated:** 2026-10-06  
**Author:** Brone Social Nav Team
