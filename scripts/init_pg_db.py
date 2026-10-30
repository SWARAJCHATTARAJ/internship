import os
# Set DATABASE_URL here for initialization. Replace with your provided connection string.
DATABASE_URL = "postgresql://neondb_owner:npg_hCpk8bBxJV3l@ep-dawn-recipe-b5a6gotn-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ['DATABASE_URL'] = DATABASE_URL

# Importing data.db will call init_db() and create the table
import sys
import os as _os
PROJECT_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

import data.db
print('Postgres init attempted using DATABASE_URL')
