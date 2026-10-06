# Scented Bubbles Cloud Deployment Guide (Render + Supabase)

This guide documents how to deploy **Scented Bubbles** to **Render** (Application) with **Supabase** (PostgreSQL & Storage) with **zero data loss**.

---

## 1. Safety & Data Preservation
Your local SQLite database contains active products, variants, orders, and settings.
We have created automated backup tools:

1. **Physical File Backup**: `scented_bubbles.db.backup`
2. **JSON Data Backup**: `data_backup.json` (572 records across all 17 tables)
3. **SQL Dump Backup**: `data_backup.sql`

To re-export backups at any time, run:
```bash
python -m flask export-data
```

---

## 2. Step 1: Create Your Supabase Project (Database & Media)

1. Go to [https://supabase.com](https://supabase.com) and create a new project.
2. Under **Project Settings -> Database**:
   * Find **Connection String** (URI). Select **Transaction Pooler (Port 6543)** or **Direct (Port 5432)**.
   * Format: `postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`
3. Under **Storage**:
   * Click **New Bucket**.
   * Name it: `media`
   * Toggle **Public bucket** to `ON` (so product images can be viewed publicly by shoppers).
   * Under **Project Settings -> API**, copy:
     * **Project URL**: (e.g. `https://xyzcompany.supabase.co`)
     * **Service Role Key (secret)** or **Anon Key**.

---

## 3. Step 2: Migrate All Local Data into Supabase (0 Data Loss)

Before deploying or running on Render, transfer all your local catalog, users, and orders directly to Supabase with one command:

```bash
python -m flask migrate-to-supabase --target "postgresql://postgres.[REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
```
*(Alternatively, you can run `python scripts/migrate_to_supabase.py --target "..."`).*

**What this script does:**
* Creates all relational tables on Supabase automatically.
* Copies all records across all tables (Admins, Products, Variants, Images, Combos, Banners, Customers, Orders, Payments, History).
* Automatically syncs and advances PostgreSQL auto-increment sequences (`setval`) so future orders and products never clash with existing IDs.
* Verifies row counts table-by-table.

---

## 4. Step 3: Deploy to Render

1. Go to [https://render.com](https://render.com) and click **New -> Web Service**.
2. Connect your Git repository.
3. Configure the service:
   * **Name**: `scented-bubbles`
   * **Environment**: `Python 3`
   * **Region**: Choose closest to your customers (e.g., `Singapore` or `Frankfurt`).
   * **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   * **Start Command**:
     ```bash
     gunicorn wsgi:app --workers 2 --threads 4 --timeout 120
     ```
4. In the **Environment Variables** tab, add:

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Enables production security & caching |
| `SECRET_KEY` | *(Generate a random 32-char string)* | Session encryption |
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres` | Your Supabase connection string |
| `STORAGE_BACKEND` | `supabase` | Enables Supabase cloud media storage |
| `SUPABASE_URL` | `https://[PROJECT-REF].supabase.co` | Your Supabase project URL |
| `SUPABASE_KEY` | `[YOUR-SUPABASE-SERVICE-KEY]` | Secret service role API key |
| `SUPABASE_BUCKET`| `media` | Name of your storage bucket |

5. Click **Create Web Service**.
   * Render will build the dependencies, run `gunicorn`, and launch your live store!

---

## 5. Local Development Remains Untouched
* When you run `python run.py` locally without `DATABASE_URL`, it continues reading and writing to your local `scented_bubbles.db` file.
* Your local offline development will never touch or wipe production data.
