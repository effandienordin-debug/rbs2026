import sqlite3
import pandas as pd
from sqlalchemy import create_engine

# --- KONFIGURASI ---
# 1. Path ke database lama anda (SQLite)
sqlite_db = "rbs_database.db" 

# 2. Connection String Supabase anda (Ambil dari Streamlit Secrets atau Supabase Dashboard)
# Pastikan bermula dengan postgresql://
supabase_url = "postgresql://postgres:[PASSWORD]@db.xxxxxx.supabase.co:5432/postgres"

# --- PROSES MIGRASI ---
def migrate():
    try:
        # Connect ke kedua-dua DB
        sqlite_conn = sqlite3.connect(sqlite_db)
        supabase_engine = create_engine(supabase_url)
        
        # Senarai table yang ingin dipindahkan
        tables = ['users', 'reviewers', 'applicants', 'applicant_assignments', 'reviews']
        
        print("🚀 Memulakan proses migrasi data...")
        
        for table in tables:
            print(f"📦 Memindahkan table: {table}...")
            
            # 1. Baca data dari SQLite guna Pandas
            df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
            
            if not df.empty:
                # 2. Tolak data ke Supabase
                # 'if_exists=append' supaya data masuk ke table yang kita dah 'init' tadi
                # 'index=False' supaya ID tidak bertindih jika guna SERIAL
                df.to_sql(table, supabase_engine, if_exists='append', index=False)
                print(f"✅ Berjaya pindah {len(df)} rekod dalam {table}.")
            else:
                print(f"ℹ️ Table {table} kosong, skip.")
        
        print("\n✨ Migrasi selesai sepenuhnya!")
        
    except Exception as e:
        print(f"❌ Ralat berlaku: {e}")
    finally:
        sqlite_conn.close()

if __name__ == "__main__":
    migrate()
