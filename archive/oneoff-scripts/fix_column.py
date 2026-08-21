import psycopg2
conn = psycopg2.connect('postgresql://postgres:TCGlFLKDPkBvRMpQsbTEAAObldUtqYcL@metro.proxy.rlwy.net:45559/railway')
cur = conn.cursor()
cur.execute('ALTER TABLE productions ADD COLUMN IF NOT EXISTS "episodeCount" INTEGER')
conn.commit()
cur.close()
conn.close()
print('Column added')
