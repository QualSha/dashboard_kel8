from django.shortcuts import render
import pandas as pd
import json
import os
from django.conf import settings

def dashboard(request):
    # Sesuaikan path ini dengan lokasi file Anda di komputer!
    path_excel = r"C:\Users\Haykal Pasha Siregar\Documents\Visualisasi Data\dataset_komoditas.xlsx"
    path_geojson = r"C:\Users\Haykal Pasha Siregar\Documents\Visualisasi Data\choropleth_map.geojson"
    
    hero_stats, scene1_kpi, map_data, chart_data, geojson_data = {}, {}, {}, {}, {}
    scene2_metrics, scene3_metrics, scene3_insight, scene4_json = {}, {}, {}, {}
    trend_data, seasonal_data = {}, {}

    try:
        # 1. BACA DATA PANGAN
        df = pd.read_excel(path_excel)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        col_prov = 'Provinsi' if 'Provinsi' in df.columns else 'Province'
        
        def format_num(val): return f"{val:,.0f}"
        
        # HERO STATS
        latest_date = df['Date'].max()
        df_latest = df[df['Date'] == latest_date]
        last_year_date = latest_date - pd.DateOffset(years=1)
        df_last_year = df[df['Date'] == last_year_date]
        
        def get_hero_stats(col_name):
            val_now = df_latest[col_name].mean()
            val_prev = df_last_year[col_name].mean()
            yoy = ((val_now - val_prev) / val_prev) * 100
            return {'val': format_num(val_now), 'yoy': f"+{yoy:.1f}% YoY" if yoy > 0 else f"{yoy:.1f}% YoY"}

        hero_stats = {
            'sapi': get_hero_stats('Daging_Sapi'),
            'ayam': get_hero_stats('Daging_Ayam'),
            'telur': get_hero_stats('Telur_Ayam'),
        }

        # SCENE 1: AGREGAT PROVINSI
        df_avg = df.groupby(col_prov)[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].mean().reset_index()

        max_sapi_idx = df_avg['Daging_Sapi'].idxmax()
        max_ayam_idx = df_avg['Daging_Ayam'].idxmax()
        max_telur_idx = df_avg['Telur_Ayam'].idxmax()

        scene1_kpi = {
            'sapi': {'prov': df_avg.loc[max_sapi_idx, col_prov], 'val': format_num(df_avg.loc[max_sapi_idx, 'Daging_Sapi'])},
            'ayam': {'prov': df_avg.loc[max_ayam_idx, col_prov], 'val': format_num(df_avg.loc[max_ayam_idx, 'Daging_Ayam'])},
            'telur': {'prov': df_avg.loc[max_telur_idx, col_prov], 'val': format_num(df_avg.loc[max_telur_idx, 'Telur_Ayam'])}
        }

        # DATA UNTUK PETA (Dictionary)
        map_data = {
            'sapi': dict(zip(df_avg[col_prov], df_avg['Daging_Sapi'])),
            'ayam': dict(zip(df_avg[col_prov], df_avg['Daging_Ayam'])),
            'telur': dict(zip(df_avg[col_prov], df_avg['Telur_Ayam']))
        }

        # DATA UNTUK CHART (Top 5)
        top_sapi = df_avg.nlargest(5, 'Daging_Sapi')
        top_ayam = df_avg.nlargest(5, 'Daging_Ayam')
        top_telur = df_avg.nlargest(5, 'Telur_Ayam')
        chart_data = {
            'sapi': {'labels': top_sapi[col_prov].tolist(), 'data': top_sapi['Daging_Sapi'].tolist()},
            'ayam': {'labels': top_ayam[col_prov].tolist(), 'data': top_ayam['Daging_Ayam'].tolist()},
            'telur': {'labels': top_telur[col_prov].tolist(), 'data': top_telur['Telur_Ayam'].tolist()}
        }

        # 2. BACA FILE GEOJSON
        if os.path.exists(path_geojson):
            with open(path_geojson, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
        else:
            print("WARNING: File choropleth_map.geojson tidak ditemukan di path tersebut.")

        # Scene 02
        # --- PERHITUNGAN NASIONAL (TIME SERIES) ---
        # Group by date untuk mendapatkan rata-rata harga nasional setiap harinya
        df_nat = df.groupby('Date')[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].mean().reset_index().sort_values('Date')
        
        # Resample ke Bulanan untuk menghitung lonjakan (Spike) yang lebih stabil
        df_monthly = df_nat.set_index('Date').resample('MS').mean()
        
        # 1. Lonjakan Paling Tajam (Month-over-Month)
        mom_change = df_monthly.pct_change()
        max_spike_val = mom_change.max().max() # Nilai % tertinggi
        max_spike_col = mom_change.max().idxmax() # Komoditasnya
        # Mencari periode terjadinya
        spike_date = mom_change[max_spike_col].idxmax()
        spike_period = f"{max_spike_col.replace('_',' ')}, {spike_date.strftime('%b')} {(spike_date - pd.DateOffset(months=1)).strftime('%b')} {spike_date.year}"

        # 2. Kenaikan Kumulatif (Harga Akhir vs Harga Awal)
        cum_change = (df_nat.iloc[-1][['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']] / df_nat.iloc[0][['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']]) - 1
        max_cum_val = cum_change.max()
        max_cum_col = cum_change.idxmax()
        cum_period = f"{max_cum_col.replace('_',' ')}, {df_nat.iloc[0]['Date'].strftime('%b %Y')} vs {df_nat.iloc[-1]['Date'].strftime('%b %Y')}"

        # 3. Koefisien Variasi (CV) = Std Dev / Mean (Makin kecil makin stabil)
        cv = df_nat[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].std() / df_nat[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].mean()
        most_stable_col = cv.idxmin()
        
        scene2_metrics = {
            'spike': {'val': f"+{max_spike_val*100:.1f}%", 'unit': spike_period},
            'cum': {'val': f"+{max_cum_val*100:.1f}%", 'unit': cum_period},
            'stable': {'val': most_stable_col.replace('Daging_','').replace('_',' '), 'unit': "Koef. variasi terendah secara nasional"}
        }
        
        df['Month'] = df['Date'].dt.month
        # Hitung rata-rata harga berdasarkan bulan kalender
        df_season = df.groupby('Month')[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].mean().reset_index().sort_values('Month')
        
        months_name = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        
        def get_season_metrics(col):
            min_val = df_season[col].min()
            max_val = df_season[col].max()
            min_month_idx = df_season[col].idxmin()
            max_month_idx = df_season[col].idxmax()
            amp = ((max_val - min_val) / min_val) * 100 # Perhitungan Amplitudo (%)
            
            return {
                'min_month': months_name[int(df_season.loc[min_month_idx, 'Month']) - 1],
                'max_month': months_name[int(df_season.loc[max_month_idx, 'Month']) - 1],
                'amp': f"+{amp:.1f}%",
                'data': df_season[col].tolist()
            }
            
        scene3_metrics = {
            'sapi': get_season_metrics('Daging_Sapi'),
            'ayam': get_season_metrics('Daging_Ayam'),
            'telur': get_season_metrics('Telur_Ayam')
        }
        
        seasonal_data = {
            'labels': months_name,
            'sapi': scene3_metrics['sapi']['data'],
            'ayam': scene3_metrics['ayam']['data'],
            'telur': scene3_metrics['telur']['data']
        }
        
        
        # Data untuk Line Chart (Nasional)
        trend_data = {
            'labels': df_nat['Date'].dt.strftime('%b %y').tolist(),
            'sapi': df_nat['Daging_Sapi'].tolist(),
            'ayam': df_nat['Daging_Ayam'].tolist(),
            'telur': df_nat['Telur_Ayam'].tolist()
        }
        
       # 1. Load Dataset UMP
        ump_path = r"C:\Users\Haykal Pasha Siregar\Documents\Visualisasi Data\dashboard_uts\dataset_ump.xlsx" 
        ump_df = pd.read_excel(ump_path)
        
        # Jadikan semua nama kolom string dan hapus spasi berlebih agar aman
        ump_df.columns = ump_df.columns.astype(str).str.strip()
        
        # Gunakan kolom '2025', bukan 'UMP'
        ump_dict = dict(zip(ump_df['Province'], ump_df['2026']))
        
        # 2. Perhitungan Insight Scene 03 (Pola Musiman)
        # (Asumsi df_season sudah dihitung dari rata-rata per bulan)
        amp_sapi_raw = ((df_season['Daging_Sapi'].max() - df_season['Daging_Sapi'].min()) / df_season['Daging_Sapi'].min()) * 100
        amp_ayam_raw = ((df_season['Daging_Ayam'].max() - df_season['Daging_Ayam'].min()) / df_season['Daging_Ayam'].min()) * 100
        ratio_ayam_sapi = amp_ayam_raw / amp_sapi_raw if amp_sapi_raw > 0 else 0

        scene3_insight = {
            'amp_sapi': f"{amp_sapi_raw:.1f}%",
            'amp_ayam': f"{amp_ayam_raw:.1f}%",
            'ratio': f"{ratio_ayam_sapi:.1f}x"
        }

        # 3. Scene 04: Ketimpangan Wilayah
        # Pemetaan Pulau untuk Scatter Plot (Sesuai desain native)
        island_map = {
            "Aceh": "Sumatera", "Sumatera Utara": "Sumatera", "Sumatera Barat": "Sumatera", "Riau": "Sumatera", 
            "Kepulauan Riau": "Sumatera", "Jambi": "Sumatera", "Bengkulu": "Sumatera", "Sumatera Selatan": "Sumatera", 
            "Bangka Belitung": "Sumatera", "Lampung": "Sumatera", 
            "Banten": "Jawa", "Jawa Barat": "Jawa", "DKI Jakarta": "Jawa", "Jawa Tengah": "Jawa", 
            "DI Yogyakarta": "Jawa", "Jawa Timur": "Jawa", 
            "Bali": "Nusa Tenggara & Bali", "Nusa Tenggara Barat": "Nusa Tenggara & Bali", "Nusa Tenggara Timur": "Nusa Tenggara & Bali",
            "Kalimantan Barat": "Kalimantan", "Kalimantan Tengah": "Kalimantan", "Kalimantan Selatan": "Kalimantan", 
            "Kalimantan Timur": "Kalimantan", "Kalimantan Utara": "Kalimantan",
            "Sulawesi Utara": "Sulawesi", "Gorontalo": "Sulawesi", "Sulawesi Tengah": "Sulawesi", 
            "Sulawesi Barat": "Sulawesi", "Sulawesi Selatan": "Sulawesi", "Sulawesi Tenggara": "Sulawesi",
            "Maluku": "Maluku & Papua", "Maluku Utara": "Maluku & Papua", "Papua Barat": "Maluku & Papua", "Papua": "Maluku & Papua"
        }

        # Ambil rata-rata harga provinsi pada periode terakhir (df_latest)
        prov_latest = df_latest.groupby(col_prov)[['Daging_Sapi', 'Daging_Ayam', 'Telur_Ayam']].mean().reset_index()

        scatter_data = []
        for _, row in prov_latest.iterrows():
            p = row[col_prov] # Gunakan col_prov di sini
            if p in ump_dict:
                scatter_data.append({
                    "x": int(ump_dict[p]),
                    "y": float(row['Daging_Sapi']),
                    "label": p,
                    "island": island_map.get(p, "Lainnya")
                })

        scene4_json = {
            "scatter": scatter_data,
            "lollipop": {
                "sapi": {
                    "max_val": float(prov_latest['Daging_Sapi'].max()),
                    "max_prov": prov_latest.loc[prov_latest['Daging_Sapi'].idxmax(), col_prov],
                    "min_val": float(prov_latest['Daging_Sapi'].min()),
                    "min_prov": prov_latest.loc[prov_latest['Daging_Sapi'].idxmin(), col_prov]
                },
                "ayam": {
                    "max_val": float(prov_latest['Daging_Ayam'].max()),
                    "max_prov": prov_latest.loc[prov_latest['Daging_Ayam'].idxmax(), col_prov],
                    "min_val": float(prov_latest['Daging_Ayam'].min()),
                    "min_prov": prov_latest.loc[prov_latest['Daging_Ayam'].idxmin(), col_prov]
                },
                "telur": {
                    "max_val": float(prov_latest['Telur_Ayam'].max()),
                    "max_prov": prov_latest.loc[prov_latest['Telur_Ayam'].idxmax(), col_prov],
                    "min_val": float(prov_latest['Telur_Ayam'].min()),
                    "min_prov": prov_latest.loc[prov_latest['Telur_Ayam'].idxmin(), col_prov]
                }
            }
        }
        
    except Exception as e:
        print(f"Error pada views: {e}")

    context = {
        'hero': hero_stats,
        'scene1_kpi': scene1_kpi,
        'scene2': scene2_metrics,
        'trend_json': json.dumps(trend_data) if trend_data else "{}",
        'scene3_metrics': scene3_metrics,
        'scene3_insight': scene3_insight,
        'scene4_json': json.dumps(scene4_json) if scene4_json else "{}",
        'seasonal_json': json.dumps(seasonal_data) if seasonal_data else "{}",
        'map_data_json': json.dumps(map_data) if map_data else "{}",
        'chart_data_json': json.dumps(chart_data) if chart_data else "{}",
        'geojson_data': json.dumps(geojson_data) if geojson_data else "{}"
    }
    
    return render(request, 'dashboard.html', context)