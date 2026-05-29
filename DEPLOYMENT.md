# Deploying Daycare Manager (Sprout) to Vercel + Supabase

The Supabase database is already provisioned and all tables are created. You just
need to (1) push the code, (2) set 3 environment variables in Vercel. ~5 minutes.

---

## What's already done (by Claude)

- ✅ Supabase project **daycare-manager** created (org: verchertechnologies, region us-east-1)
- ✅ All 11 tables created in Postgres (daycares, users, parents, children, classes,
  attendance, daily_reports, incidents, invoices, payments, parent_child)
- ✅ Billing code committed-ready locally (staged), tests passing 37/37

---

## Step 1 — Push the code to GitHub

Open Terminal on your Mac and run these (one block):

```bash
cd ~/Documents/"Code Projects"/"software team"/daycare-manager
rm -f .git/index.lock          # clears the stale lock from the sandbox
echo "*.db-journal" >> .gitignore
git add -A
git commit -m "Add billing module, fix frontend API wiring, scope daycares to tenant"
git push origin main
```

If Vercel is connected to this GitHub repo, the push auto-starts a deploy.
(If it doesn't, open the Vercel project → Deployments → Redeploy.)

---

## Step 2 — Get your database connection string (Supabase)

1. Go to https://supabase.com/dashboard/project/puywghcsoxtvcniienjd
2. Click **Connect** (top bar) → **Transaction pooler** (this mode is required for
   Vercel's serverless functions).
3. Copy the connection string. It looks like:

   ```
   postgresql://postgres.puywghcsoxtvcniienjd:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

4. Replace `[YOUR-PASSWORD]` with your database password. If you don't know it,
   go to **Settings → Database → Reset database password**, set a new one, and use that.
5. Add `?sslmode=require` to the end:

   ```
   postgresql://postgres.puywghcsoxtvcniienjd:YOURPASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```

---

## Step 3 — Set environment variables in Vercel

Vercel → project **daycare-manager** → **Settings → Environment Variables**.
Add these three (Production + Preview):

| Name           | Value                                                                 |
|----------------|-----------------------------------------------------------------------|
| `DATABASE_URL` | the full connection string from Step 2                                |
| `SECRET_KEY`   | `des7-osmhCeGLfMNNNIpJiHCb6nrMq-jQOTewBaGpgaHZIv_9OSdY6aZSjC0GBs1`     |
| `ENVIRONMENT`  | `production`                                                          |

> ⚠️ `SECRET_KEY` must be a fixed value (don't regenerate). If it changes, everyone
> gets logged out. The one above was generated for you — keep it secret.

After saving env vars, **redeploy** (Vercel → Deployments → ⋯ → Redeploy) so they
take effect.

---

## Step 4 — Verify

1. Open your Vercel URL (e.g. `https://daycare-manager-xxxx.vercel.app`).
2. Sign up → create your center → add a child → create an invoice → record a payment.
3. If anything errors, check Vercel → your deployment → **Runtime Logs**.

Tell Claude once you've pushed and set the env vars — it can pull the deployment
status and logs to confirm everything is healthy.

---

## Notes

- The app currently records card payments for **tracking only** (no real charge).
  Adding real Stripe processing is a later step once you've validated demand.
- The database has a free-tier 500MB / pausing-after-inactivity limit — plenty to start.
- Connection string host/port may differ slightly; always copy the exact one Supabase
  shows in the Connect dialog.
