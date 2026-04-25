from django.shortcuts import render
import pandas as pd
import json
import os

def dashboard(request):
    # Sesuaikan path ini dengan lokasi file Anda di komputer!
    path_excel = r"C:\Users\Haykal Pasha Siregar\Documents\Visualisasi Data\dataset_komoditas.xlsx"
    path_geojson = r"C:\Users\Haykal Pasha Siregar\Documents\Visualisasi Data\choropleth_map.geojson"
    
    hero_stats, scene1_kpi, map_data, chart_data, geojson_data = {}, {}, {}, {}, {}

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

    except Exception as e:
        print(f"Error pada views: {e}")

    context = {
        'hero': hero_stats,
        'scene1_kpi': scene1_kpi,
        'map_data_json': json.dumps(map_data),
        'chart_data_json': json.dumps(chart_data),
        'geojson_data': json.dumps(geojson_data) # Mengirim GeoJSON ke template
    }
    
    return render(request, 'dashboard.html', context)